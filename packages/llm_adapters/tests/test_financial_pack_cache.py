"""Regression tests for bounded financial decision-pack caching."""

import pytest

from llm_adapters.tools import financial_pack_cache as cache


class Adapter:
    pass


@pytest.fixture(autouse=True)
def clean_cache():
    cache.reset_pack_cache()
    yield
    cache.reset_pack_cache()


def test_cache_expiration(monkeypatch):
    adapter = Adapter()
    clock = [100.0]

    monkeypatch.setattr(
        cache, "monotonic", lambda: clock[0]
    )

    pack = {"valuation": 100}

    cache._set_cached_pack(adapter, "INFY", pack)

    assert cache._get_cached_pack(
        adapter, "INFY"
    ) == pack

    clock[0] += cache._PACK_CACHE_TTL_SECONDS + 1

    assert cache._get_cached_pack(
        adapter, "INFY"
    ) is None


def test_cache_capacity(monkeypatch):
    adapter = Adapter()

    monkeypatch.setattr(
        cache, "_PACK_CACHE_MAX_ENTRIES", 2
    )

    cache._set_cached_pack(adapter, "A", {"v": 1})
    cache._set_cached_pack(adapter, "B", {"v": 2})
    cache._set_cached_pack(adapter, "C", {"v": 3})

    assert cache._get_cached_pack(adapter, "A") is None
    assert cache._get_cached_pack(adapter, "B") == {"v": 2}
    assert cache._get_cached_pack(adapter, "C") == {"v": 3}


def test_adapter_isolation():
    first = Adapter()
    second = Adapter()

    cache._set_cached_pack(
        first, "INFY", {"value": 100}
    )

    assert cache._get_cached_pack(
        second, "INFY"
    ) is None


def test_ticker_normalization():
    adapter = Adapter()

    cache._set_cached_pack(
        adapter, " infy ", {"value": 100}
    )

    assert cache._get_cached_pack(
        adapter, "INFY"
    ) == {"value": 100}


def test_selective_invalidation():
    first = Adapter()
    second = Adapter()

    cache._set_cached_pack(first, "INFY", {"v": 1})
    cache._set_cached_pack(second, "INFY", {"v": 2})

    cache.reset_pack_cache(first)

    assert cache._get_cached_pack(first, "INFY") is None
    assert cache._get_cached_pack(second, "INFY") == {"v": 2}


def test_global_invalidation():
    adapter = Adapter()

    cache._set_cached_pack(adapter, "INFY", {"v": 1})

    cache.reset_pack_cache()

    assert cache._get_cached_pack(adapter, "INFY") is None


def test_recently_accessed_entry_preserved(monkeypatch):
    adapter = Adapter()

    monkeypatch.setattr(
        cache, "_PACK_CACHE_MAX_ENTRIES", 2
    )

    cache._set_cached_pack(adapter, "A", {"v": 1})
    cache._set_cached_pack(adapter, "B", {"v": 2})

    cache._get_cached_pack(adapter, "A")

    cache._set_cached_pack(adapter, "C", {"v": 3})

    assert cache._get_cached_pack(adapter, "B") is None
    assert cache._get_cached_pack(adapter, "A") == {"v": 1}
