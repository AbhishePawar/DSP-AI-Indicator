"""Rate limiting — in-memory foundation (PEP-002)."""

from __future__ import annotations

import time
from threading import Lock

from production_platform.production.interfaces import RateLimitPort

__all__ = ["InMemoryRateLimitPort", "ensure_rate_limit_port"]


class InMemoryRateLimitPort:
    """Process-local sliding-window counter — not Redis."""

    def __init__(self) -> None:
        self._events: dict[str, list[float]] = {}
        self._lock = Lock()

    def allow(self, key: str, *, limit: int, window_seconds: float) -> bool:
        if limit <= 0:
            return False
        now = time.monotonic()
        window = float(window_seconds)
        with self._lock:
            bucket = [t for t in self._events.get(key, []) if now - t < window]
            if len(bucket) >= limit:
                self._events[key] = bucket
                return False
            bucket.append(now)
            self._events[key] = bucket
            return True


def ensure_rate_limit_port(port: RateLimitPort | None) -> RateLimitPort:
    return port if port is not None else InMemoryRateLimitPort()
