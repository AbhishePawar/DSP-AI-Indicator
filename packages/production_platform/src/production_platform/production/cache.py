"""Cache — in-memory provider-neutral adapter."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

from production_platform.production.interfaces import CachePort

__all__ = ["InMemoryCachePort"]


class InMemoryCachePort:
    """Process-local TTL cache — not Redis."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lock = Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires = item
            if expires is not None and time.monotonic() >= expires:
                del self._data[key]
                return None
            return value

    def set(
        self, key: str, value: Any, *, ttl_seconds: float | None = None
    ) -> None:
        expires = None
        if ttl_seconds is not None:
            expires = time.monotonic() + float(ttl_seconds)
        with self._lock:
            self._data[key] = (value, expires)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def ensure_cache_port(port: CachePort | None) -> CachePort:
    return port if port is not None else InMemoryCachePort()
