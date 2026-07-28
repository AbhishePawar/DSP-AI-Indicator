"""Distributed locking — in-memory foundation (PEP-002)."""

from __future__ import annotations

import time
from threading import Lock

from production_platform.production.interfaces import LockPort

__all__ = ["InMemoryLockPort", "ensure_lock_port"]


class InMemoryLockPort:
    """Process-local locks with TTL — not Redis Redlock."""

    def __init__(self) -> None:
        self._locks: dict[str, float] = {}
        self._guard = Lock()

    def acquire(self, name: str, *, ttl_seconds: float = 30.0) -> bool:
        now = time.monotonic()
        with self._guard:
            expires = self._locks.get(name)
            if expires is not None and expires > now:
                return False
            self._locks[name] = now + float(ttl_seconds)
            return True

    def release(self, name: str) -> None:
        with self._guard:
            self._locks.pop(name, None)


def ensure_lock_port(port: LockPort | None) -> LockPort:
    return port if port is not None else InMemoryLockPort()
