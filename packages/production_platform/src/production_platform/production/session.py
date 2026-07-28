"""Session storage — in-memory foundation (PEP-002)."""

from __future__ import annotations

import time
from threading import Lock
from typing import Any

from production_platform.production.interfaces import SessionPort

__all__ = ["InMemorySessionPort", "ensure_session_port"]


class InMemorySessionPort:
    """Process-local session map — not Redis / DB sessions."""

    def __init__(self) -> None:
        self._data: dict[str, tuple[dict[str, Any], float | None]] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            item = self._data.get(session_id)
            if item is None:
                return None
            payload, expires = item
            if expires is not None and time.monotonic() >= expires:
                del self._data[session_id]
                return None
            return dict(payload)

    def set(
        self, session_id: str, payload: dict[str, Any], *, ttl_seconds: float | None = None
    ) -> None:
        expires = None
        if ttl_seconds is not None:
            expires = time.monotonic() + float(ttl_seconds)
        with self._lock:
            self._data[session_id] = (dict(payload), expires)

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)


def ensure_session_port(port: SessionPort | None) -> SessionPort:
    return port if port is not None else InMemorySessionPort()
