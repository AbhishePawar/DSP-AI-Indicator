"""Historical time-series port + service (EPIC-D004).

Reuses D001 resilience primitives. Retrieval/validation only —
no indicators, TA, valuation, or scoring.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine.cache import CachePort, InMemoryCache
from data_engine.exceptions import ProviderRequestError
from data_engine.historical_series.models import (
    AuthenticatedHistoricalBundle,
    HistoricalCompanyIdentity,
)
from data_engine.historical_series.validation import (
    validate_authenticated_historical_bundle,
)
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RetryPolicy,
)

__all__ = [
    "HistoricalSeriesPort",
    "HistoricalSeriesQuery",
    "HistoricalSeriesService",
    "HistoricalSeriesServiceMetrics",
    "HistoricalProviderHealth",
]

_LOG = logging.getLogger("data_engine.historical_series")


@dataclass(frozen=True, slots=True)
class HistoricalSeriesQuery:
    """Read-only date-range query for authenticated historical series."""

    instrument: Instrument
    series_kind: str  # ohlcv | market_cap | volume | enterprise_value | fundamentals | ratios
    frequency: str | None = "daily"  # daily|weekly|monthly (ohlcv); ignored otherwise
    start_date: date | None = None
    end_date: date | None = None
    limit: int = 500


@dataclass(frozen=True, slots=True)
class HistoricalProviderHealth:
    provider_id: str
    healthy: bool
    authenticated: bool
    detail: str
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        from data_engine.historical_series.models import utc_now

        return {
            "provider_id": self.provider_id,
            "healthy": self.healthy,
            "authenticated": self.authenticated,
            "detail": self.detail,
            "checked_at": self.checked_at or utc_now().isoformat(),
        }


class HistoricalSeriesPort(ABC):
    """Port for authenticated historical time-series retrieval."""

    @abstractmethod
    def get_series(
        self, query: HistoricalSeriesQuery
    ) -> AuthenticatedHistoricalBundle | None:
        """Return authenticated series, or ``None`` when unavailable."""

    @abstractmethod
    def resolve_company(
        self, instrument: Instrument
    ) -> HistoricalCompanyIdentity | None:
        """Resolve company identifiers."""

    @abstractmethod
    def health(self) -> HistoricalProviderHealth:
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""


@dataclass
class HistoricalSeriesServiceMetrics:
    requests: int = 0
    cache_hits: int = 0
    successes: int = 0
    failures: int = 0
    unavailable: int = 0
    rejected_invalid: int = 0

    def snapshot(self) -> dict[str, int]:
        return {
            "requests": self.requests,
            "cache_hits": self.cache_hits,
            "successes": self.successes,
            "failures": self.failures,
            "unavailable": self.unavailable,
            "rejected_invalid": self.rejected_invalid,
        }


class HistoricalSeriesService:
    """Cache + rate-limit + retry + circuit-breaker around HistoricalSeriesPort."""

    def __init__(
        self,
        provider: HistoricalSeriesPort,
        *,
        cache: CachePort | None = None,
        cache_ttl_seconds: float = 300.0,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry: RetryPolicy | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._provider = provider
        self._cache = cache or InMemoryCache()
        self._cache_ttl = cache_ttl_seconds
        self._rate = rate_limiter
        self._breaker = circuit_breaker or CircuitBreaker()
        self._retry = retry or RetryPolicy()
        self._timeout = timeout_seconds
        self.metrics = HistoricalSeriesServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def resolve_company(
        self, instrument: Instrument
    ) -> HistoricalCompanyIdentity | None:
        return self._provider.resolve_company(instrument)

    def get_series(
        self, query: HistoricalSeriesQuery
    ) -> AuthenticatedHistoricalBundle | None:
        self.metrics.requests += 1
        symbol = query.instrument.symbol.strip().upper()
        kind = query.series_kind.strip().lower()
        freq = (query.frequency or "").strip().lower()
        start = query.start_date.isoformat() if query.start_date else ""
        end = query.end_date.isoformat() if query.end_date else ""
        cache_key = (
            f"historical_series:{self.provider_id}:{symbol}:{kind}:{freq}:"
            f"{start}:{end}:{query.limit}"
        )
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthenticatedHistoricalBundle):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            _LOG.info(
                "historical_series_cache_hit",
                extra={"symbol": symbol, "provider": self.provider_id, "kind": kind},
            )
            return replace(
                cached,
                provenance=replace(cached.provenance, cache_hit=True),
            )

        def _call() -> AuthenticatedHistoricalBundle | None:
            self._breaker.before_call()
            if self._rate is not None:
                self._rate.acquire(timeout_seconds=self._timeout)
            started = time.monotonic()
            try:
                bundle = self._provider.get_series(query)
            except Exception:
                self._breaker.record_failure()
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("historical series provider timed out")
            if bundle is None:
                self._breaker.record_success()
                return None
            try:
                validate_authenticated_historical_bundle(bundle)
            except Exception:
                self.metrics.rejected_invalid += 1
                self._breaker.record_failure()
                _LOG.warning(
                    "historical_series_rejected_invalid",
                    extra={"symbol": symbol, "provider": self.provider_id},
                )
                raise
            self._breaker.record_success()
            return bundle

        try:
            bundle = self._retry.run(_call)
        except CircuitOpenError:
            self.metrics.failures += 1
            _LOG.error(
                "historical_series_circuit_open",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "historical_series_failure",
                extra={
                    "symbol": symbol,
                    "provider": self.provider_id,
                    "error": str(exc),
                },
            )
            raise

        if bundle is None:
            self.metrics.unavailable += 1
            _LOG.info(
                "historical_series_unavailable",
                extra={"symbol": symbol, "provider": self.provider_id, "kind": kind},
            )
            return None

        stamped = replace(
            bundle,
            provenance=replace(
                bundle.provenance,
                request_id=bundle.provenance.request_id or str(uuid.uuid4()),
                cache_hit=False,
            ),
        )
        self._cache.set(cache_key, stamped, ttl_seconds=self._cache_ttl)
        self.metrics.successes += 1
        _LOG.info(
            "historical_series_ok",
            extra={
                "symbol": symbol,
                "provider": self.provider_id,
                "kind": kind,
                "bars": len(stamped.bars),
                "points": len(stamped.points),
                "snapshots": len(stamped.snapshots),
                "request_id": stamped.provenance.request_id,
            },
        )
        return stamped

    def health(self) -> HistoricalProviderHealth:
        return self._provider.health()
