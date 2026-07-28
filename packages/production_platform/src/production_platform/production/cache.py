"""Cache — in-memory + fallback + invalidation (PEP-002)."""

from __future__ import annotations

import fnmatch
import time
from threading import Lock
from typing import Any

from production_platform.production.exceptions import ProviderError
from production_platform.production.interfaces import CachePort

__all__ = [
    "FallbackCachePort",
    "InMemoryCachePort",
    "PatternCacheInvalidation",
    "ensure_cache_port",
]


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

    def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
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

    def keys(self) -> tuple[str, ...]:
        with self._lock:
            now = time.monotonic()
            alive = [
                k
                for k, (_v, exp) in self._data.items()
                if exp is None or exp > now
            ]
            return tuple(sorted(alive))


class FallbackCachePort:
    """Prefer primary cache; degrade to fallback when primary raises ProviderError."""

    def __init__(self, primary: CachePort, fallback: CachePort) -> None:
        self._primary = primary
        self._fallback = fallback
        self._using_fallback = False

    @property
    def using_fallback(self) -> bool:
        return self._using_fallback

    def get(self, key: str) -> Any | None:
        try:
            value = self._primary.get(key)
            self._using_fallback = False
            return value
        except ProviderError:
            self._using_fallback = True
            return self._fallback.get(key)

    def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        try:
            self._primary.set(key, value, ttl_seconds=ttl_seconds)
            self._using_fallback = False
        except ProviderError:
            self._using_fallback = True
            self._fallback.set(key, value, ttl_seconds=ttl_seconds)

    def delete(self, key: str) -> None:
        try:
            self._primary.delete(key)
            self._using_fallback = False
        except ProviderError:
            self._using_fallback = True
            self._fallback.delete(key)


class PatternCacheInvalidation:
    """Invalidation helper for caches that expose keys or pattern delete."""

    def __init__(self, cache: CachePort) -> None:
        self._cache = cache

    def invalidate(self, key: str) -> None:
        self._cache.delete(key)

    def invalidate_pattern(self, pattern: str) -> int:
        deleter = getattr(self._cache, "delete_pattern", None)
        if callable(deleter):
            return int(deleter(pattern))  # type: ignore[misc]
        keys_fn = getattr(self._cache, "keys", None)
        if not callable(keys_fn):
            raise ProviderError("cache does not support pattern invalidation")
        matched = [k for k in keys_fn() if fnmatch.fnmatch(k, pattern)]
        for key in matched:
            self._cache.delete(key)
        return len(matched)


def ensure_cache_port(port: CachePort | None) -> CachePort:
    return port if port is not None else InMemoryCachePort()
