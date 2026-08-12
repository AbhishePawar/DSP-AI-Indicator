"""News provider port + resilient single-provider service.

Reuses the D001 resilience primitives (cache, rate limit, retry,
circuit breaker, timeout) exactly like ``corporate_actions.service``.
Multi-provider priority/failover across several ``NewsProviderPort``
implementations is layered on top by ``news.registry`` /
``dsp_platform.news`` via
:class:`~data_engine.connector_framework.failover.FailoverGroup`.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, replace
from datetime import datetime

from contracts.domain.instrument import Instrument
from data_engine.cache import CachePort, InMemoryCache
from data_engine.connector_framework.models import ProviderHealth, utc_now
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    RetryPolicy,
)
from data_engine.news.models import AuthenticatedNewsFeed
from data_engine.news.validation import validate_authenticated_news_feed

__all__ = [
    "NewsProviderPort",
    "NewsQuery",
    "NewsService",
    "NewsServiceMetrics",
]

_LOG = logging.getLogger("data_engine.news")


@dataclass(frozen=True, slots=True)
class NewsQuery:
    """Read-only query for authenticated company news."""

    instrument: Instrument
    limit: int = 20
    since: datetime | None = None


class NewsProviderPort(ABC):
    """Port for authenticated company news retrieval."""

    @abstractmethod
    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        """Return an authenticated news feed, or ``None`` when unavailable.

        Implementations must never invent articles. Invalid payloads
        must raise or return ``None`` after validation failure.
        """

    @abstractmethod
    def health(self) -> ProviderHealth:
        """Provider health for readiness probes."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable provider identifier."""


@dataclass
class NewsServiceMetrics:
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


class NewsService:
    """Cache + rate-limit + retry + circuit-breaker around NewsProviderPort."""

    def __init__(
        self,
        provider: NewsProviderPort,
        *,
        cache: CachePort | None = None,
        cache_ttl_seconds: float = 120.0,
        rate_limiter: RateLimiter | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        retry: RetryPolicy | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._provider = provider
        self._cache = cache or InMemoryCache()
        self._cache_ttl = cache_ttl_seconds
        self._rate = rate_limiter
        self._breaker = circuit_breaker or CircuitBreaker()
        self._retry = retry or RetryPolicy()
        self._timeout = timeout_seconds
        self.metrics = NewsServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def get_news(self, query: NewsQuery) -> AuthenticatedNewsFeed | None:
        self.metrics.requests += 1
        symbol = query.instrument.symbol.strip().upper()
        since = query.since.isoformat() if query.since else ""
        cache_key = f"news:{self.provider_id}:{symbol}:{query.limit}:{since}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, AuthenticatedNewsFeed):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            _LOG.info(
                "news_cache_hit", extra={"symbol": symbol, "provider": self.provider_id}
            )
            return replace(cached, provenance=replace(cached.provenance, cache_hit=True))

        def _call() -> AuthenticatedNewsFeed | None:
            self._breaker.before_call()
            if self._rate is not None:
                self._rate.acquire(timeout_seconds=self._timeout)
            started = time.monotonic()
            try:
                feed = self._provider.get_news(query)
            except Exception:
                self._breaker.record_failure()
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("news provider timed out")
            if feed is None:
                self._breaker.record_success()
                return None
            try:
                validate_authenticated_news_feed(feed)
            except Exception:
                self.metrics.rejected_invalid += 1
                self._breaker.record_failure()
                _LOG.warning(
                    "news_rejected_invalid",
                    extra={"symbol": symbol, "provider": self.provider_id},
                )
                raise
            self._breaker.record_success()
            return feed

        try:
            feed = self._retry.run(_call)
        except CircuitOpenError:
            self.metrics.failures += 1
            _LOG.error(
                "news_circuit_open", extra={"symbol": symbol, "provider": self.provider_id}
            )
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "news_failure",
                extra={"symbol": symbol, "provider": self.provider_id, "error": str(exc)},
            )
            raise

        if feed is None:
            self.metrics.unavailable += 1
            _LOG.info(
                "news_unavailable", extra={"symbol": symbol, "provider": self.provider_id}
            )
            return None

        stamped = replace(
            feed,
            provenance=replace(
                feed.provenance,
                request_id=feed.provenance.request_id or str(uuid.uuid4()),
                cache_hit=False,
            ),
        )
        self._cache.set(cache_key, stamped, ttl_seconds=self._cache_ttl)
        self.metrics.successes += 1
        _LOG.info(
            "news_ok",
            extra={
                "symbol": symbol,
                "provider": self.provider_id,
                "articles": len(stamped.articles),
                "request_id": stamped.provenance.request_id,
            },
        )
        return stamped

    def health(self) -> ProviderHealth:
        return self._provider.health()
