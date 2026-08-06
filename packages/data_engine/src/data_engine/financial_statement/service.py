"""Financial statement port + service (EPIC-D002).

Reuses D001 resilience primitives (rate limit, retry, circuit breaker).
Retrieval and validation only — no calculations.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine.cache import CachePort, InMemoryCache
from data_engine.exceptions import ProviderRequestError
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    CompanyIdentity,
)
from data_engine.financial_statement.validation import validate_authenticated_statements
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RetryPolicy,
)

__all__ = [
    "FinancialStatementPort",
    "FinancialStatementService",
    "FinancialStatementServiceMetrics",
    "StatementProviderHealth",
    "StatementQuery",
]

_LOG = logging.getLogger("data_engine.financial_statement")


@dataclass(frozen=True, slots=True)
class StatementQuery:
    """Read-only query for authenticated statements."""

    instrument: Instrument
    period_type: str | None = None  # annual | quarterly | ttm | None=all
    limit: int = 8
    include_restated: bool = True


@dataclass(frozen=True, slots=True)
class StatementProviderHealth:
    provider_id: str
    healthy: bool
    authenticated: bool
    detail: str
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        from data_engine.financial_statement.models import utc_now

        return {
            "provider_id": self.provider_id,
            "healthy": self.healthy,
            "authenticated": self.authenticated,
            "detail": self.detail,
            "checked_at": self.checked_at or utc_now().isoformat(),
        }


class FinancialStatementPort(ABC):
    """Port for authenticated financial statement retrieval (RS-003)."""

    @abstractmethod
    def get_statements(
        self, query: StatementQuery
    ) -> AuthenticatedFinancialStatements | None:
        """Return authenticated statements, or ``None`` when unavailable.

        Must never invent numbers. Invalid payloads must raise or return None.
        """

    @abstractmethod
    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        """Resolve company identifiers (symbol/exchange → provider id)."""

    @abstractmethod
    def health(self) -> StatementProviderHealth:
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""


@dataclass
class FinancialStatementServiceMetrics:
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


class FinancialStatementService:
    """Cache + rate-limit + retry + circuit-breaker around FinancialStatementPort."""

    def __init__(
        self,
        provider: FinancialStatementPort,
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
        self.metrics = FinancialStatementServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def resolve_company(self, instrument: Instrument) -> CompanyIdentity | None:
        return self._provider.resolve_company(instrument)

    def get_statements(
        self, query: StatementQuery
    ) -> AuthenticatedFinancialStatements | None:
        self.metrics.requests += 1
        symbol = query.instrument.symbol.strip().upper()
        period = (query.period_type or "all").strip().lower()
        cache_key = (
            f"financial_statement:{self.provider_id}:{symbol}:{period}:"
            f"{query.limit}:{int(query.include_restated)}"
        )
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthenticatedFinancialStatements):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            _LOG.info(
                "financial_statement_cache_hit",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            return replace(
                cached,
                provenance=replace(cached.provenance, cache_hit=True),
            )

        def _call() -> AuthenticatedFinancialStatements | None:
            self._breaker.before_call()
            if self._rate is not None:
                self._rate.acquire(timeout_seconds=self._timeout)
            started = time.monotonic()
            try:
                bundle = self._provider.get_statements(query)
            except Exception:
                self._breaker.record_failure()
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("financial statement provider timed out")
            if bundle is None:
                self._breaker.record_success()
                return None
            try:
                validate_authenticated_statements(bundle)
            except Exception:
                self.metrics.rejected_invalid += 1
                self._breaker.record_failure()
                _LOG.warning(
                    "financial_statement_rejected_invalid",
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
                "financial_statement_circuit_open",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "financial_statement_failure",
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
                "financial_statement_unavailable",
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
            "financial_statement_ok",
            extra={
                "symbol": symbol,
                "provider": self.provider_id,
                "periods": len(stamped.periods),
                "request_id": stamped.provenance.request_id,
            },
        )
        return stamped

    def health(self) -> StatementProviderHealth:
        return self._provider.health()
