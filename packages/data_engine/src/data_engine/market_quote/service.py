"""Market quote port + resilience primitives (EPIC-D001)."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from contracts.domain.instrument import Instrument
from data_engine.cache import CachePort, InMemoryCache
from data_engine.exceptions import (
    DataEngineError,
    DataValidationError,
    NormalizationError,
    ProviderRequestError,
)
from data_engine.market_quote.models import AuthenticatedMarketQuote
from data_engine.market_quote.validation import validate_authenticated_quote

__all__ = [
    "CircuitBreaker",
    "CircuitOpenError",
    "MarketQuotePort",
    "MarketQuoteService",
    "MarketQuoteServiceMetrics",
    "RateLimiter",
    "RetryPolicy",
    "QuoteProviderHealth",
    "is_provider_circuit_failure",
]

_LOG = logging.getLogger("data_engine.market_quote")
T = TypeVar("T")


class CircuitOpenError(DataEngineError):
    """Raised when a named provider circuit breaker is open."""

    def __init__(self, message: str | None = None, *, domain: str = "circuit") -> None:
        self.domain = domain
        super().__init__(message or f"{domain} circuit breaker open")


def is_provider_circuit_failure(exc: BaseException) -> bool:
    """True when ``exc`` is a provider/transport fault that may open a breaker.

    Deterministic domain/data validation must not poison provider circuits.
    """
    if isinstance(exc, CircuitOpenError):
        return False
    if isinstance(exc, (DataValidationError, NormalizationError)):
        return False
    return True


class MarketQuotePort(ABC):
    """Port for authenticated market quote snapshots (RS-002)."""

    @abstractmethod
    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        """Return an authenticated quote, or ``None`` when unavailable.

        Implementations must never invent numbers. Invalid payloads must
        raise or return ``None`` after validation failure.
        """

    @abstractmethod
    def health(self) -> "QuoteProviderHealth":
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""


@dataclass(frozen=True, slots=True)
class QuoteProviderHealth:
    provider_id: str
    healthy: bool
    authenticated: bool
    detail: str
    checked_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "healthy": self.healthy,
            "authenticated": self.authenticated,
            "detail": self.detail,
            "checked_at": self.checked_at.isoformat(),
        }


@dataclass
class RateLimiter:
    """Simple token-bucket rate limiter (requests per minute)."""

    requests_per_minute: int
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _tokens: float = field(init=False)
    _updated: float = field(init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.requests_per_minute)
        self._updated = time.monotonic()

    def acquire(self, timeout_seconds: float = 5.0) -> None:
        deadline = time.monotonic() + timeout_seconds
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._updated
                self._updated = now
                self._tokens = min(
                    float(self.requests_per_minute),
                    self._tokens + elapsed * (self.requests_per_minute / 60.0),
                )
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
            if time.monotonic() >= deadline:
                raise ProviderRequestError("market quote rate limit exceeded")
            time.sleep(0.02)


@dataclass
class CircuitBreaker:
    """Failure-threshold circuit breaker for one protected service domain."""

    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0
    name: str = "circuit"
    _failures: int = 0
    _opened_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def before_call(self) -> None:
        with self._lock:
            if self._opened_at is None:
                return
            if time.monotonic() - self._opened_at >= self.recovery_timeout_seconds:
                self._opened_at = None
                self._failures = 0
                return
            raise CircuitOpenError(
                f"{self.name} circuit breaker open",
                domain=self.name,
            )

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()

    def record_if_provider_failure(self, exc: BaseException) -> bool:
        """Count provider/transport faults only. Return True if counted."""
        if not is_provider_circuit_failure(exc):
            return False
        self.record_failure()
        return True

    @property
    def failure_count(self) -> int:
        with self._lock:
            return self._failures

    @property
    def is_open(self) -> bool:
        with self._lock:
            if self._opened_at is None:
                return False
            return time.monotonic() - self._opened_at < self.recovery_timeout_seconds


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.05

    def run(self, fn: Callable[[], T]) -> T:
        last: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except CircuitOpenError:
                raise
            except DataValidationError:
                raise
            except NormalizationError:
                raise
            except Exception as exc:  # noqa: BLE001 — bounded retry surface
                last = exc
                if attempt >= self.max_attempts:
                    break
                time.sleep(self.backoff_seconds * attempt)
        assert last is not None
        raise last


@dataclass
class MarketQuoteServiceMetrics:
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


class MarketQuoteService:
    """Cache + rate-limit + retry + circuit-breaker around MarketQuotePort."""

    def __init__(
        self,
        provider: MarketQuotePort,
        *,
        cache: CachePort | None = None,
        cache_ttl_seconds: float = 30.0,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry: RetryPolicy | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._provider = provider
        self._cache = cache or InMemoryCache()
        self._cache_ttl = cache_ttl_seconds
        self._rate = rate_limiter
        self._breaker = circuit_breaker or CircuitBreaker(name="market quote")
        self._retry = retry or RetryPolicy()
        self._timeout = timeout_seconds
        self.metrics = MarketQuoteServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def _note_protected_exception(self, exc: BaseException) -> None:
        counted = self._breaker.record_if_provider_failure(exc)
        if counted:
            return
        _LOG.info(
            "circuit_breaker_not_counted",
            extra={
                "breaker_domain": self._breaker.name,
                "failure_class": "data_validation",
                "breaker_counted": False,
                "reason": getattr(exc, "code", type(exc).__name__),
            },
        )

    def get_quote(self, instrument: Instrument) -> AuthenticatedMarketQuote | None:
        self.metrics.requests += 1
        symbol = instrument.symbol.strip().upper()
        cache_key = f"market_quote:{self.provider_id}:{symbol}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthenticatedMarketQuote):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            _LOG.info(
                "market_quote_cache_hit",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            return cached

        def _call() -> AuthenticatedMarketQuote | None:
            self._breaker.before_call()
            if self._rate is not None:
                self._rate.acquire(timeout_seconds=self._timeout)
            started = time.monotonic()
            try:
                quote = self._provider.get_quote(instrument)
            except Exception as exc:
                self._note_protected_exception(exc)
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("market quote provider timed out")
            if quote is None:
                self._breaker.record_success()
                return None
            try:
                validate_authenticated_quote(quote)
            except Exception as exc:
                self.metrics.rejected_invalid += 1
                self._note_protected_exception(exc)
                _LOG.warning(
                    "market_quote_rejected_invalid",
                    extra={"symbol": symbol, "provider": self.provider_id},
                )
                raise
            self._breaker.record_success()
            return quote

        try:
            quote = self._retry.run(_call)
        except CircuitOpenError:
            self.metrics.failures += 1
            _LOG.error(
                "market_quote_circuit_open",
                extra={
                    "symbol": symbol,
                    "provider": self.provider_id,
                    "breaker_domain": self._breaker.name,
                },
            )
            raise
        except (DataValidationError, NormalizationError):
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "market_quote_failure",
                extra={"symbol": symbol, "provider": self.provider_id, "error": str(exc)},
            )
            raise

        if quote is None:
            self.metrics.unavailable += 1
            _LOG.info(
                "market_quote_unavailable",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            return None

        # Re-stamp cache provenance flag without inventing fields
        stamped = AuthenticatedMarketQuote(
            symbol=quote.symbol,
            exchange=quote.exchange,
            currency=quote.currency,
            current_price=quote.current_price,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            previous_close=quote.previous_close,
            week_52_high=quote.week_52_high,
            week_52_low=quote.week_52_low,
            volume=quote.volume,
            average_volume=quote.average_volume,
            market_cap=quote.market_cap,
            enterprise_value=quote.enterprise_value,
            shares_outstanding=quote.shares_outstanding,
            dividend_yield=quote.dividend_yield,
            beta=quote.beta,
            provenance=type(quote.provenance)(
                provider_id=quote.provenance.provider_id,
                provider_name=quote.provenance.provider_name,
                source_type=quote.provenance.source_type,
                retrieved_at=quote.provenance.retrieved_at,
                as_of=quote.provenance.as_of,
                request_id=quote.provenance.request_id or str(uuid.uuid4()),
                cache_hit=False,
                auth_mode=quote.provenance.auth_mode,
                metadata=dict(quote.provenance.metadata),
            ),
        )
        self._cache.set(cache_key, stamped, ttl_seconds=self._cache_ttl)
        self.metrics.successes += 1
        _LOG.info(
            "market_quote_ok",
            extra={
                "symbol": symbol,
                "provider": self.provider_id,
                "request_id": stamped.provenance.request_id,
            },
        )
        return stamped

    def health(self) -> QuoteProviderHealth:
        return self._provider.health()
