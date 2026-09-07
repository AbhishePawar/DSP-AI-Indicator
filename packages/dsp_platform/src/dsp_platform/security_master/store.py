"""Security Master persistence. History is append-only.

Memory store is for tests. Production wires DatabaseSecurityMasterStore
onto the existing DatabasePort — no filesystem production universe.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from dsp_platform.security_master.models import (
    SnapshotStatus,
    UniverseSnapshot,
)

__all__ = [
    "MemorySecurityMasterStore",
    "SecurityMasterStore",
    "configure_security_master_store",
    "get_security_master_store",
    "reset_security_master_store_for_tests",
]


class MemorySecurityMasterStore:
    """Process-local store. Not production state."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._snapshots: dict[str, UniverseSnapshot] = {}
        self._current_id: str | None = None

    def save_snapshot(self, snapshot: UniverseSnapshot) -> UniverseSnapshot:
        with self._lock:
            self._snapshots[snapshot.snapshot_id] = snapshot
            if snapshot.status is not SnapshotStatus.FAILED:
                self._current_id = snapshot.snapshot_id
            return snapshot

    def current_snapshot(self) -> UniverseSnapshot | None:
        with self._lock:
            if not self._current_id:
                return None
            return self._snapshots.get(self._current_id)

    def get_snapshot(self, snapshot_id: str) -> UniverseSnapshot | None:
        with self._lock:
            return self._snapshots.get(snapshot_id)

    def list_snapshots(self, *, limit: int = 20) -> tuple[dict[str, Any], ...]:
        with self._lock:
            rows = [
                {
                    **snap.to_metadata_dict(),
                    "is_current": snap.snapshot_id == self._current_id,
                }
                for snap in self._snapshots.values()
            ]
        rows.sort(key=lambda item: str(item.get("retrieved_at") or ""), reverse=True)
        return tuple(rows[:limit])


SecurityMasterStore = MemorySecurityMasterStore

_STORE: Any | None = None
_STORE_LOCK = Lock()


def configure_security_master_store(database: Any | None = None) -> Any:
    global _STORE
    with _STORE_LOCK:
        if database is not None and all(
            hasattr(database, name) for name in ("execute", "fetchall", "ping")
        ):
            from dsp_platform.security_master.db_store import DatabaseSecurityMasterStore

            _STORE = DatabaseSecurityMasterStore(database)
        else:
            _STORE = MemorySecurityMasterStore()
        return _STORE


def get_security_master_store() -> Any:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = MemorySecurityMasterStore()
        return _STORE


def reset_security_master_store_for_tests(store: Any | None = None) -> Any:
    global _STORE
    with _STORE_LOCK:
        _STORE = store if store is not None else MemorySecurityMasterStore()
        return _STORE
