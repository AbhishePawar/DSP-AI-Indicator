"""Cache subsystem for the Data Engine.

Caching is internal infrastructure the Data Engine owns outright — unlike
external data sources, which it only ever reaches through
``data_engine.ports`` — so the abstract ``CachePort`` and its reference
in-memory implementation live together in this module rather than being
split across ``ports``/``adapters``.

No real caching backend (Redis, disk, a distributed cache, etc.) is
implemented here — only the interface and a minimal in-memory reference
implementation used for tests and for services that don't yet need a
persistent cache.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

__all__ = ["CachePort", "InMemoryCache"]


class CachePort(ABC, Generic[K, V]):
    """Port for a generic key/value cache with optional expiration."""

    @abstractmethod
    def get(self, key: K) -> V | None:
        """Retrieve a cached value.

        Args:
            key: Cache key to look up.

        Returns:
            The cached value, or ``None`` if absent or expired.
        """

    @abstractmethod
    def set(self, key: K, value: V, *, ttl_seconds: float | None = None) -> None:
        """Store a value in the cache.

        Args:
            key: Cache key to store the value under.
            value: Value to cache.
            ttl_seconds: Optional time-to-live in seconds. ``None`` means
                the value never expires on its own.
        """

    @abstractmethod
    def invalidate(self, key: K) -> None:
        """Remove a value from the cache, if present.

        Args:
            key: Cache key to remove.
        """


class InMemoryCache(CachePort[K, V]):
    """Minimal in-process cache backed by a plain dictionary.

    Intended for tests and early development, not production use across
    multiple processes. Not thread-safe — the same limitation flagged for
    ``core.registry.Registry`` applies here for the same reason (a plain
    ``dict`` with no locking).
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory cache."""
        self._values: dict[K, V] = {}
        self._expires_at: dict[K, float] = {}

    def get(self, key: K) -> V | None:
        """Retrieve a cached value, honoring expiration.

        Args:
            key: Cache key to look up.

        Returns:
            The cached value, or ``None`` if absent or expired.
        """
        if key not in self._values:
            return None
        expires_at = self._expires_at.get(key)
        if expires_at is not None and time.monotonic() >= expires_at:
            self._values.pop(key, None)
            self._expires_at.pop(key, None)
            return None
        return self._values[key]

    def set(self, key: K, value: V, *, ttl_seconds: float | None = None) -> None:
        """Store a value, optionally with a time-to-live.

        Args:
            key: Cache key to store the value under.
            value: Value to cache.
            ttl_seconds: Optional time-to-live in seconds. ``None`` means
                the value never expires on its own.
        """
        self._values[key] = value
        if ttl_seconds is not None:
            self._expires_at[key] = time.monotonic() + ttl_seconds
        else:
            self._expires_at.pop(key, None)

    def invalidate(self, key: K) -> None:
        """Remove a value from the cache, if present.

        Args:
            key: Cache key to remove.
        """
        self._values.pop(key, None)
        self._expires_at.pop(key, None)
