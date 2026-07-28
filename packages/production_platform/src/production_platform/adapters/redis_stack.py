"""Redis adapters — cache, rate limit, lock, session (PEP-002 / ADR-PEP-0005).

Vendor SDK loaded via importlib (lazy) — never a static ``import redis``.
"""

from __future__ import annotations

import importlib
import json
import time
from typing import Any

from production_platform.production.exceptions import ConfigurationError, ProviderError

__all__ = [
    "RedisCachePort",
    "RedisLockPort",
    "RedisRateLimitPort",
    "RedisSessionPort",
    "try_build_redis_stack",
]


def _load_redis() -> Any:
    try:
        return importlib.import_module("redis")
    except ImportError as exc:
        raise ProviderError(
            "redis package is not installed; pip install 'production-platform[redis]'"
        ) from exc


def _client(url: str, *, socket_timeout: float) -> Any:
    if not url.strip():
        raise ConfigurationError("redis url must not be empty")
    redis_mod = _load_redis()
    try:
        return redis_mod.Redis.from_url(
            url,
            socket_connect_timeout=socket_timeout,
            socket_timeout=socket_timeout,
            decode_responses=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"redis connect failed: {exc}") from exc


class RedisCachePort:
    """CachePort backed by Redis strings (JSON-encoded values)."""

    def __init__(
        self, url: str, *, key_prefix: str = "dsp", socket_timeout: float = 2.0
    ) -> None:
        self._prefix = key_prefix.rstrip(":")
        self._client = _client(url, socket_timeout=socket_timeout)
        self._ping()

    def _k(self, key: str) -> bytes:
        return f"{self._prefix}:cache:{key}".encode()

    def _ping(self) -> None:
        try:
            if not self._client.ping():
                raise ProviderError("redis ping failed")
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis unavailable: {exc}") from exc

    def get(self, key: str) -> Any | None:
        try:
            raw = self._client.get(self._k(key))
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis get failed: {exc}") from exc
        if raw is None:
            return None
        return json.loads(raw.decode("utf-8"))

    def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        payload = json.dumps(value).encode("utf-8")
        try:
            if ttl_seconds is None:
                self._client.set(self._k(key), payload)
            else:
                self._client.setex(self._k(key), int(max(1, ttl_seconds)), payload)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis set failed: {exc}") from exc

    def delete(self, key: str) -> None:
        try:
            self._client.delete(self._k(key))
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis delete failed: {exc}") from exc

    def delete_pattern(self, pattern: str) -> int:
        match = f"{self._prefix}:cache:{pattern}".encode()
        deleted = 0
        try:
            for key in self._client.scan_iter(match=match, count=100):
                self._client.delete(key)
                deleted += 1
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis delete_pattern failed: {exc}") from exc
        return deleted


class RedisRateLimitPort:
    """Fixed-window rate limiter using Redis INCR + EXPIRE."""

    def __init__(
        self, url: str, *, key_prefix: str = "dsp", socket_timeout: float = 2.0
    ) -> None:
        self._prefix = key_prefix.rstrip(":")
        self._client = _client(url, socket_timeout=socket_timeout)

    def allow(self, key: str, *, limit: int, window_seconds: float) -> bool:
        if limit <= 0:
            return False
        bucket = int(time.time() // max(window_seconds, 0.001))
        redis_key = f"{self._prefix}:rl:{key}:{bucket}".encode()
        try:
            count = int(self._client.incr(redis_key))
            if count == 1:
                self._client.expire(redis_key, int(max(1, window_seconds)))
            return count <= limit
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis rate limit failed: {exc}") from exc


class RedisLockPort:
    """Simple Redis SET NX EX lock."""

    def __init__(
        self, url: str, *, key_prefix: str = "dsp", socket_timeout: float = 2.0
    ) -> None:
        self._prefix = key_prefix.rstrip(":")
        self._client = _client(url, socket_timeout=socket_timeout)

    def _k(self, name: str) -> bytes:
        return f"{self._prefix}:lock:{name}".encode()

    def acquire(self, name: str, *, ttl_seconds: float = 30.0) -> bool:
        try:
            return bool(
                self._client.set(
                    self._k(name), b"1", nx=True, ex=int(max(1, ttl_seconds))
                )
            )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis lock acquire failed: {exc}") from exc

    def release(self, name: str) -> None:
        try:
            self._client.delete(self._k(name))
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis lock release failed: {exc}") from exc


class RedisSessionPort:
    """Session blobs stored as Redis JSON strings."""

    def __init__(
        self, url: str, *, key_prefix: str = "dsp", socket_timeout: float = 2.0
    ) -> None:
        self._prefix = key_prefix.rstrip(":")
        self._client = _client(url, socket_timeout=socket_timeout)

    def _k(self, session_id: str) -> bytes:
        return f"{self._prefix}:session:{session_id}".encode()

    def get(self, session_id: str) -> dict[str, Any] | None:
        try:
            raw = self._client.get(self._k(session_id))
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis session get failed: {exc}") from exc
        if raw is None:
            return None
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None

    def set(
        self,
        session_id: str,
        payload: dict[str, Any],
        *,
        ttl_seconds: float | None = None,
    ) -> None:
        raw = json.dumps(payload).encode("utf-8")
        try:
            if ttl_seconds is None:
                self._client.set(self._k(session_id), raw)
            else:
                self._client.setex(
                    self._k(session_id), int(max(1, ttl_seconds)), raw
                )
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis session set failed: {exc}") from exc

    def delete(self, session_id: str) -> None:
        try:
            self._client.delete(self._k(session_id))
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(f"redis session delete failed: {exc}") from exc


def try_build_redis_stack(
    url: str | None,
    *,
    key_prefix: str = "dsp",
    socket_timeout: float = 2.0,
) -> dict[str, Any] | None:
    """Build Redis-backed ports when URL + driver available; else None."""
    if not url:
        return None
    try:
        cache = RedisCachePort(
            url, key_prefix=key_prefix, socket_timeout=socket_timeout
        )
        return {
            "cache": cache,
            "rate_limit": RedisRateLimitPort(
                url, key_prefix=key_prefix, socket_timeout=socket_timeout
            ),
            "lock": RedisLockPort(
                url, key_prefix=key_prefix, socket_timeout=socket_timeout
            ),
            "session": RedisSessionPort(
                url, key_prefix=key_prefix, socket_timeout=socket_timeout
            ),
        }
    except (ConfigurationError, ProviderError, ImportError):
        return None
