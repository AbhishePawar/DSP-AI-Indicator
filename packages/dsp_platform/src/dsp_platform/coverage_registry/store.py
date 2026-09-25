"""Append-only coverage registry store (process-local + durable subclass)."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock, RLock
from typing import Any

from dsp_platform.coverage_registry.models import CoverageRecord
from dsp_platform.durable_snapshot import (
    ensure_snapshot_table,
    load_snapshot,
    save_snapshot,
)

__all__ = [
    "COVERAGE_SNAPSHOT_KEY",
    "COVERAGE_SNAPSHOT_TABLE",
    "CoverageRegistryStore",
    "DatabaseCoverageRegistryStore",
    "get_coverage_registry_store",
    "reset_coverage_registry_store_for_tests",
]

COVERAGE_SNAPSHOT_TABLE = "coverage_registry_snapshots"
COVERAGE_SNAPSHOT_KEY = "coverage_registry_v1"


class CoverageRegistryStore:
    """Thread-safe append-only record log with per-symbol indexes."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._records: list[CoverageRecord] = []
        self._by_symbol: dict[str, list[CoverageRecord]] = {}

    # -- writes -----------------------------------------------------------
    def append(self, record: CoverageRecord) -> CoverageRecord:
        with self._lock:
            self._records.append(record)
            self._by_symbol.setdefault(record.symbol.upper(), []).append(record)
            return record

    # -- reads ------------------------------------------------------------
    def list_all(self) -> tuple[CoverageRecord, ...]:
        with self._lock:
            return tuple(self._records)

    def list_by_symbol(self, symbol: str) -> tuple[CoverageRecord, ...]:
        with self._lock:
            return tuple(self._by_symbol.get(symbol.strip().upper(), ()))

    def latest_by_symbol(self) -> dict[str, CoverageRecord]:
        with self._lock:
            return {sym: rows[-1] for sym, rows in self._by_symbol.items() if rows}

    def latest_for(self, symbol: str) -> CoverageRecord | None:
        rows = self.list_by_symbol(symbol)
        return rows[-1] if rows else None

    def list_by_owner(self, user_id: str) -> tuple[CoverageRecord, ...]:
        with self._lock:
            return tuple(r for r in self._records if r.owner_user_id == user_id)

    def count(self) -> int:
        with self._lock:
            return len(self._records)

    # -- state ------------------------------------------------------------
    def export_state(self) -> dict[str, Any]:
        with self._lock:
            return {"records": [r.to_dict() for r in self._records]}

    def import_state(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._records = []
            self._by_symbol = {}
            for raw in payload.get("records") or []:
                try:
                    record = CoverageRecord.from_dict(raw)
                except Exception:  # noqa: BLE001 — skip corrupt rows, never fabricate
                    continue
                if not record.symbol:
                    continue
                self._records.append(record)
                self._by_symbol.setdefault(record.symbol, []).append(record)


_META = frozenset(
    {"ensure_schema", "ensure_fresh", "hydrate", "flush", "export_state", "import_state"}
)


class DatabaseCoverageRegistryStore(CoverageRegistryStore):
    """Registry hydrated from / flushed to a shared DatabasePort (P0-06 pattern)."""

    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self.ensure_schema()
        self.hydrate()

    def ensure_schema(self) -> None:
        ensure_snapshot_table(self._db, COVERAGE_SNAPSHOT_TABLE)

    def ensure_fresh(self) -> None:
        with self._persist_lock:
            self.hydrate()

    def hydrate(self) -> None:
        payload = load_snapshot(
            self._db, table=COVERAGE_SNAPSHOT_TABLE, snapshot_key=COVERAGE_SNAPSHOT_KEY
        )
        if payload:
            self.import_state(payload)

    def flush(self) -> None:
        with self._persist_lock:
            save_snapshot(
                self._db,
                table=COVERAGE_SNAPSHOT_TABLE,
                snapshot_key=COVERAGE_SNAPSHOT_KEY,
                payload=self.export_state(),
                updated_at=datetime.now(tz=UTC).isoformat(),
            )

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_") or name in _META:
            return object.__getattribute__(self, name)
        attr = object.__getattribute__(self, name)
        if not callable(attr):
            return attr

        def bound(*args: Any, **kwargs: Any) -> Any:
            object.__getattribute__(self, "ensure_fresh")()
            result = attr(*args, **kwargs)
            if name == "append":
                object.__getattribute__(self, "flush")()
            return result

        return bound


_STORE_LOCK = Lock()
_STORE: CoverageRegistryStore | None = None


def get_coverage_registry_store(database: Any | None = None) -> CoverageRegistryStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = (
                DatabaseCoverageRegistryStore(database)
                if database is not None
                else CoverageRegistryStore()
            )
        return _STORE


def reset_coverage_registry_store_for_tests(
    store: CoverageRegistryStore | None = None,
) -> None:
    global _STORE
    with _STORE_LOCK:
        _STORE = store
