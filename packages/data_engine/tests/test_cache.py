"""Tests for data_engine.cache."""

import time

import pytest

from data_engine.cache import CachePort, InMemoryCache


class TestCachePort:
    """Tests for the CachePort abstract interface."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            CachePort()  # type: ignore[abstract]


class TestInMemoryCache:
    """Tests for the InMemoryCache reference implementation."""

    def test_get_missing_key_returns_none(self) -> None:
        cache: InMemoryCache[str, int] = InMemoryCache()
        assert cache.get("missing") is None

    def test_set_then_get_returns_value(self) -> None:
        cache: InMemoryCache[str, int] = InMemoryCache()
        cache.set("a", 1)
        assert cache.get("a") == 1

    def test_invalidate_removes_value(self) -> None:
        cache: InMemoryCache[str, int] = InMemoryCache()
        cache.set("a", 1)
        cache.invalidate("a")
        assert cache.get("a") is None

    def test_invalidate_missing_key_is_a_no_op(self) -> None:
        cache: InMemoryCache[str, int] = InMemoryCache()
        cache.invalidate("missing")  # must not raise

    def test_value_expires_after_ttl(self) -> None:
        cache: InMemoryCache[str, int] = InMemoryCache()
        cache.set("a", 1, ttl_seconds=0.01)
        time.sleep(0.02)
        assert cache.get("a") is None

    def test_value_without_ttl_never_expires(self) -> None:
        cache: InMemoryCache[str, int] = InMemoryCache()
        cache.set("a", 1)
        time.sleep(0.01)
        assert cache.get("a") == 1

    def test_re_setting_without_ttl_clears_previous_expiration(self) -> None:
        cache: InMemoryCache[str, int] = InMemoryCache()
        cache.set("a", 1, ttl_seconds=0.01)
        cache.set("a", 2)
        time.sleep(0.02)
        assert cache.get("a") == 2
