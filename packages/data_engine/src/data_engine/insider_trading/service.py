"""Insider trading provider port + resilient single-provider service."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import date

from contracts.domain.instrument import Instrument
from data_engine.cache import CachePort, InMemoryCache
from data_engine.connector_framework.models import ProviderHealth
from data_engine.exceptions import ProviderRequestError
from data_engine.insider_trading.models import AuthenticatedInsiderActivity
from data_engine.insider_trading.validation import validate_authenticated_insider_activity
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RetryPolicy,
)

__all__ = [
    "InsiderTradingProviderPort",
    "InsiderTradingQuery",
    "InsiderTradingService",
    "InsiderTradingServiceMetrics",
]

_LOG = logging.getLogger("data_engine.insider_trading")


@dataclass(frozen=True, slots=True)
class InsiderTradingQuery:
    """Read-only query for authenticated insider trading activity."""

    instrument: Instrument
    start_date: date | None = None
    end_date: date | None = None
    limit: int = 50


class InsiderTradingProviderPort(ABC):
    """Port for authenticated insider trading retrieval."""

    @abstractmethod
    def get_insider_activity(
        self, query: InsiderTradingQuery
    ) -> AuthenticatedInsiderActivity | None:
        """Return authenticated insider activity, or ``None`` when unavailable."""

    @abstractmethod
    def health(self) -> ProviderHealth:
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""


@dataclass
class InsiderTradingServiceMetrics:
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


class InsiderTradingService:
    """Cache + rate-limit + retry + circuit-breaker around InsiderTradingProviderPort."""

    def __init__(
        self,
        provider: InsiderTradingProviderPort,
        *,
        cache: CachePort | None = None,
        cache_ttl_seconds: float = 900.0,
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
        self.metrics = InsiderTradingServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def get_insider_activity(
        self, query: InsiderTradingQuery
    ) -> AuthenticatedInsiderActivity | None:
        self.metrics.requests += 1
        symbol = query.instrument.symbol.strip().upper()
        start = query.start_date.isoformat() if query.start_date else ""
        end = query.end_date.isoformat() if query.end_date else ""
        cache_key = f"insider:{self.provider_id}:{symbol}:{start}:{end}:{query.limit}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthenticatedInsiderActivity):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            _LOG.info(
                "insider_cache_hit", extra={"symbol": symbol, "provider": self.provider_id}
            )
            return replace(cached, provenance=replace(cached.provenance, cache_hit=True))

        def _call() -> AuthenticatedInsiderActivity | None:
            self._breaker.before_call()
            if self._rate is not None:
                self._rate.acquire(timeout_seconds=self._timeout)
            started = time.monotonic()
            try:
                bundle = self._provider.get_insider_activity(query)
            except Exception:
                self._breaker.record_failure()
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("insider trading provider timed out")
            if bundle is None:
                self._breaker.record_success()
                return None
            try:
                validate_authenticated_insider_activity(bundle)
            except Exception:
                self.metrics.rejected_invalid += 1
                self._breaker.record_failure()
                _LOG.warning(
                    "insider_rejected_invalid",
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
                "insider_circuit_open", extra={"symbol": symbol, "provider": self.provider_id}
            )
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "insider_failure",
                extra={"symbol": symbol, "provider": self.provider_id, "error": str(exc)},
            )
            raise

        if bundle is None:
            self.metrics.unavailable += 1
            _LOG.info(
                "insider_unavailable", extra={"symbol": symbol, "provider": self.provider_id}
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
            "insider_ok",
            extra={
                "symbol": symbol,
                "provider": self.provider_id,
                "transactions": len(stamped.transactions),
                "request_id": stamped.provenance.request_id,
            },
        )
        return stamped

    def health(self) -> ProviderHealth:
        return self._provider.health()
