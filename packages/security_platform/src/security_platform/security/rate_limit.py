"""Simple process-local rate limiter."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock

from security_platform.security.exceptions import RateLimitError

__all__ = ["RateLimitConfig", "RateLimiter"]


@dataclass(frozen=True, slots=True)
class RateLimitConfig:
    """Token-bucket style limits per subject key."""

    max_requests: int = 120
    window_seconds: float = 60.0
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.max_requests <= 0:
            msg = "max_requests must be positive"
            raise ValueError(msg)
        if self.window_seconds <= 0:
            msg = "window_seconds must be positive"
            raise ValueError(msg)


class RateLimiter:
    """In-memory sliding-window rate limiter — not distributed."""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        self._config = config or RateLimitConfig()
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @property
    def config(self) -> RateLimitConfig:
        return self._config

    def check(self, key: str) -> None:
        """Raise ``RateLimitError`` when the key exceeds the window budget."""
        if not self._config.enabled:
            return
        now = time.monotonic()
        window = self._config.window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and (now - bucket[0]) > window:
                bucket.popleft()
            if len(bucket) >= self._config.max_requests:
                msg = (
                    f"rate limit exceeded for {key!r}: "
                    f"{self._config.max_requests}/{self._config.window_seconds}s"
                )
                raise RateLimitError(msg)
            bucket.append(now)

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._events.clear()
            else:
                self._events.pop(key, None)
