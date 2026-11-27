"""Bounded financial decision-pack cache infrastructure."""

from collections import OrderedDict
from threading import RLock
from time import monotonic
from weakref import WeakKeyDictionary


# Bounded, instance-aware financial pack cache.

_PACK_CACHE_TTL_SECONDS = 60.0
_PACK_CACHE_MAX_ENTRIES = 128
_PACK_CACHE_LOCK = RLock()
_PACK_CACHE = WeakKeyDictionary()


def _get_cached_pack(adapter, symbol):
    key = str(symbol).strip().upper()

    with _PACK_CACHE_LOCK:
        cache = _PACK_CACHE.get(adapter)

        if cache is None:
            return None

        entry = cache.get(key)

        if entry is None:
            return None

        expires_at, pack = entry

        if monotonic() >= expires_at:
            cache.pop(key, None)
            return None

        cache.move_to_end(key)
        return pack


def _set_cached_pack(adapter, symbol, pack):
    key = str(symbol).strip().upper()

    with _PACK_CACHE_LOCK:
        cache = _PACK_CACHE.setdefault(
            adapter, OrderedDict()
        )

        now = monotonic()

        for expired_key in list(cache):
            if cache[expired_key][0] <= now:
                cache.pop(expired_key, None)

        cache[key] = (
            now + _PACK_CACHE_TTL_SECONDS,
            pack,
        )

        cache.move_to_end(key)

        while len(cache) > _PACK_CACHE_MAX_ENTRIES:
            cache.popitem(last=False)


def reset_pack_cache(adapter=None):
    """Reset cached financial packs."""

    with _PACK_CACHE_LOCK:
        if adapter is None:
            _PACK_CACHE.clear()
        else:
            _PACK_CACHE.pop(adapter, None)
