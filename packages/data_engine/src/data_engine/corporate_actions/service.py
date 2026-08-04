"""Corporate actions port + service (EPIC-D003).

Reuses D001 resilience primitives. Retrieval and validation only —
no adjusted prices or financial calculations.
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
from data_engine.corporate_actions.models import (
    AuthenticatedCorporateActions,
    CorporateActionCompanyIdentity,
)
from data_engine.corporate_actions.validation import (
    validate_authenticated_corporate_actions,
)
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RetryPolicy,
)

__all__ = [
    "CorporateActionPort",
    "CorporateActionQuery",
    "CorporateActionService",
    "CorporateActionServiceMetrics",
    "CorporateActionProviderHealth",
]

_LOG = logging.getLogger("data_engine.corporate_actions")


@dataclass(frozen=True, slots=True)
class CorporateActionQuery:
    """Read-only query for authenticated corporate actions."""

    instrument: Instrument
    action_type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class CorporateActionProviderHealth:
    provider_id: str
    healthy: bool
    authenticated: bool
    detail: str
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        from data_engine.corporate_actions.models import utc_now

        return {
            "provider_id": self.provider_id,
            "healthy": self.healthy,
            "authenticated": self.authenticated,
            "detail": self.detail,
            "checked_at": self.checked_at or utc_now().isoformat(),
        }


class CorporateActionPort(ABC):
    """Port for authenticated corporate action retrieval."""

    @abstractmethod
    def get_actions(
        self, query: CorporateActionQuery
    ) -> AuthenticatedCorporateActions | None:
        """Return authenticated events, or ``None`` when unavailable."""

    @abstractmethod
    def resolve_company(
        self, instrument: Instrument
    ) -> CorporateActionCompanyIdentity | None:
        """Resolve company identifiers."""

    @abstractmethod
    def health(self) -> CorporateActionProviderHealth:
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""


@dataclass
class CorporateActionServiceMetrics:
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


class CorporateActionService:
    """Cache + rate-limit + retry + circuit-breaker around CorporateActionPort."""

    def __init__(
        self,
        provider: CorporateActionPort,
        *,
        cache: CachePort | None = None,
        cache_ttl_seconds: float = 300.0,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry: RetryPolicy | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        self._provider = provider
        self._cache = cache or InMemoryCache()
        self._cache_ttl = cache_ttl_seconds
        self._rate = rate_limiter
        self._breaker = circuit_breaker or CircuitBreaker()
        self._retry = retry or RetryPolicy()
        self._timeout = timeout_seconds
        self.metrics = CorporateActionServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def resolve_company(
        self, instrument: Instrument
    ) -> CorporateActionCompanyIdentity | None:
        return self._provider.resolve_company(instrument)

    def get_actions(
        self, query: CorporateActionQuery
    ) -> AuthenticatedCorporateActions | None:
        self.metrics.requests += 1
        symbol = query.instrument.symbol.strip().upper()
        action = (query.action_type or "all").strip().lower()
        start = query.start_date.isoformat() if query.start_date else ""
        end = query.end_date.isoformat() if query.end_date else ""
        cache_key = (
            f"corporate_actions:{self.provider_id}:{symbol}:{action}:"
            f"{start}:{end}:{query.limit}"
        )
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthenticatedCorporateActions):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            _LOG.info(
                "corporate_actions_cache_hit",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            return replace(
                cached,
                provenance=replace(cached.provenance, cache_hit=True),
            )

        def _call() -> AuthenticatedCorporateActions | None:
            self._breaker.before_call()
            if self._rate is not None:
                self._rate.acquire(timeout_seconds=self._timeout)
            started = time.monotonic()
            try:
                bundle = self._provider.get_actions(query)
            except Exception:
                self._breaker.record_failure()
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("corporate actions provider timed out")
            if bundle is None:
                self._breaker.record_success()
                return None
            try:
                validate_authenticated_corporate_actions(bundle)
            except Exception:
                self.metrics.rejected_invalid += 1
                self._breaker.record_failure()
                _LOG.warning(
                    "corporate_actions_rejected_invalid",
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
                "corporate_actions_circuit_open",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "corporate_actions_failure",
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
                "corporate_actions_unavailable",
                extra={"symbol": symbol, "provider": self.provider_id},
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
            "corporate_actions_ok",
            extra={
                "symbol": symbol,
                "provider": self.provider_id,
                "events": len(stamped.events),
                "request_id": stamped.provenance.request_id,
            },
        )
        return stamped

    def health(self) -> CorporateActionProviderHealth:
        return self._provider.health()
