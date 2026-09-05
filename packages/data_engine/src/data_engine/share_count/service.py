"""Share-count service — cache + retry around ShareCountPort.

Retrieval and validation only. No estimates, no derivation, no fallback.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, replace

from contracts.domain.instrument import Instrument
from data_engine.cache import CachePort, InMemoryCache
from data_engine.exceptions import ProviderRequestError
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    RetryPolicy,
)
from data_engine.share_count.models import ShareCountSnapshot
from data_engine.share_count.port import ShareCountPort, ShareCountProviderHealth
from data_engine.share_count.validation import validate_share_count_snapshot

__all__ = [
    "ShareCountService",
    "ShareCountServiceMetrics",
]

_LOG = logging.getLogger("data_engine.share_count")


@dataclass
class ShareCountServiceMetrics:
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


class ShareCountService:
    """Validated retrieval around ``ShareCountPort`` — never invents a count."""

    def __init__(
        self,
        provider: ShareCountPort,
        *,
        cache: CachePort | None = None,
        cache_ttl_seconds: float = 30.0,
        circuit_breaker: CircuitBreaker | None = None,
        retry: RetryPolicy | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._provider = provider
        self._cache = cache or InMemoryCache()
        self._cache_ttl = cache_ttl_seconds
        self._breaker = circuit_breaker or CircuitBreaker()
        self._retry = retry or RetryPolicy()
        self._timeout = timeout_seconds
        self.metrics = ShareCountServiceMetrics()

    @property
    def provider_id(self) -> str:
        return self._provider.provider_id

    def get_share_count(self, instrument: Instrument) -> ShareCountSnapshot | None:
        self.metrics.requests += 1
        symbol = instrument.symbol.strip().upper()
        exchange = (instrument.exchange or "").strip().upper()
        isin = (instrument.isin or "").strip().upper()
        cache_key = f"share_count:{self.provider_id}:{symbol}:{exchange}:{isin}"
        cached = self._cache.get(cache_key)
        if isinstance(cached, ShareCountSnapshot):
            self.metrics.cache_hits += 1
            self.metrics.successes += 1
            return cached

        def _call() -> ShareCountSnapshot | None:
            self._breaker.before_call()
            started = time.monotonic()
            try:
                snapshot = self._provider.get_share_count(instrument)
            except Exception:
                self._breaker.record_failure()
                raise
            elapsed = time.monotonic() - started
            if elapsed > self._timeout:
                self._breaker.record_failure()
                raise ProviderRequestError("share count provider timed out")
            if snapshot is None:
                self._breaker.record_success()
                return None
            try:
                validate_share_count_snapshot(snapshot)
            except Exception:
                self.metrics.rejected_invalid += 1
                self._breaker.record_failure()
                _LOG.warning(
                    "share_count_rejected_invalid",
                    extra={"symbol": symbol, "provider": self.provider_id},
                )
                raise
            self._breaker.record_success()
            return snapshot

        try:
            snapshot = self._retry.run(_call)
        except CircuitOpenError:
            self.metrics.failures += 1
            raise
        except Exception as exc:
            self.metrics.failures += 1
            _LOG.exception(
                "share_count_failure",
                extra={
                    "symbol": symbol,
                    "provider": self.provider_id,
                    "error": str(exc),
                },
            )
            raise

        if snapshot is None:
            self.metrics.unavailable += 1
            _LOG.info(
                "share_count_unavailable",
                extra={"symbol": symbol, "provider": self.provider_id},
            )
            return None

        stamped = replace(
            snapshot,
            provenance=replace(
                snapshot.provenance,
                request_id=snapshot.provenance.request_id or str(uuid.uuid4()),
                cache_hit=False,
            ),
        )
        self._cache.set(cache_key, stamped, ttl_seconds=self._cache_ttl)
        self.metrics.successes += 1
        return stamped

    def health(self) -> ShareCountProviderHealth:
        return self._provider.health()
