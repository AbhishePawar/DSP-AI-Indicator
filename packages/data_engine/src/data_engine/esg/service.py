"""ESG provider port + resilient single-provider service."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace

from contracts.domain.instrument import Instrument
from data_engine.cache import CachePort, InMemoryCache
from data_engine.connector_framework.models import ProviderHealth
from data_engine.esg.models import AuthenticatedEsgScore
from data_engine.esg.validation import validate_authenticated_esg_score
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RetryPolicy,
)

__all__ = ["EsgProviderPort", "EsgQuery", "EsgService", "EsgServiceMetrics"]

_LOG = logging.getLogger("data_engine.esg")


@dataclass(frozen=True, slots=True)
class EsgQuery:
    """Read-only query for an authenticated ESG score."""

    instrument: Instrument


class EsgProviderPort(ABC):
    """Port for authenticated ESG score retrieval."""

    @abstractmethod
    def get_esg_score(self, query: EsgQuery) -> AuthenticatedEsgScore | None:
        """Return an authenticated ESG score, or ``None`` when unavailable."""

    @abstractmethod
    def health(self) -> ProviderHealth:
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""


@dataclass
class EsgServiceMetrics:
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


class EsgService:
    """Cache + rate-limit + retry + circuit-breaker around EsgProviderPort."""

    def __init__(
        self,
        provider: EsgProviderPort,
        *,
        cache: CachePort | None = None,
        cache_ttl_seconds: float = 3600.0,
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
        self.metrics = EsgServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def get_esg_score(self, query: EsgQuery) -> AuthenticatedEsgScore | None:
        self.metrics.requests += 1
        symbol = query.instrument.symbol.strip().upper()
        cache_key = f"esg:{self.provider_id}:{symbol}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthenticatedEsgScore):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            _LOG.info("esg_cache_hit", extra={"symbol": symbol, "provider": self.provider_id})
            return replace(cached, provenance=replace(cached.provenance, cache_hit=True))

        def _call() -> AuthenticatedEsgScore | None:
            self._breaker.before_call()
            if self._rate is not None:
                self._rate.acquire(timeout_seconds=self._timeout)
            started = time.monotonic()
            try:
                score = self._provider.get_esg_score(query)
            except Exception:
                self._breaker.record_failure()
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("esg provider timed out")
            if score is None:
                self._breaker.record_success()
                return None
            try:
                validate_authenticated_esg_score(score)
            except Exception:
                self.metrics.rejected_invalid += 1
                self._breaker.record_failure()
                _LOG.warning(
                    "esg_rejected_invalid", extra={"symbol": symbol, "provider": self.provider_id}
                )
                raise
            self._breaker.record_success()
            return score

        try:
            score = self._retry.run(_call)
        except CircuitOpenError:
            self.metrics.failures += 1
            _LOG.error("esg_circuit_open", extra={"symbol": symbol, "provider": self.provider_id})
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "esg_failure",
                extra={"symbol": symbol, "provider": self.provider_id, "error": str(exc)},
            )
            raise

        if score is None:
            self.metrics.unavailable += 1
            _LOG.info("esg_unavailable", extra={"symbol": symbol, "provider": self.provider_id})
            return None

        stamped = replace(
            score,
            provenance=replace(
                score.provenance,
                request_id=score.provenance.request_id or str(uuid.uuid4()),
                cache_hit=False,
            ),
        )
        self._cache.set(cache_key, stamped, ttl_seconds=self._cache_ttl)
        self.metrics.successes += 1
        _LOG.info(
            "esg_ok",
            extra={
                "symbol": symbol,
                "provider": self.provider_id,
                "request_id": stamped.provenance.request_id,
            },
        )
        return stamped

    def health(self) -> ProviderHealth:
        return self._provider.health()
