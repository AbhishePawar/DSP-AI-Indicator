"""DatabasePort-backed Security Master. Snapshots are append-only.

Writes use DatabasePort.transaction when available so a failed ingest cannot
leave a half-written current pointer. Search loads only the current snapshot's
rows and caches them in-process — it does not scan historical snapshots.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from dsp_platform.durable_snapshot import decode_snapshot_payload, encode_snapshot_payload, sql_literal
from dsp_platform.security_master.models import (
    SnapshotStatus,
    SourceTrace,
    UniverseCounts,
    UniverseSnapshot,
    record_from_dict,
)
from dsp_platform.security_master.snapshot import empty_counts

__all__ = [
    "SECURITY_MASTER_CURRENT_TABLE",
    "SECURITY_MASTER_RECORDS_TABLE",
    "SECURITY_MASTER_SNAPSHOTS_TABLE",
    "DatabaseSecurityMasterStore",
]

SECURITY_MASTER_SNAPSHOTS_TABLE = "security_universe_snapshots"
SECURITY_MASTER_RECORDS_TABLE = "security_master_records"
SECURITY_MASTER_CURRENT_TABLE = "security_universe_current"
_ADVISORY_LOCK_KEY = 814_202_614

_MIGRATIONS = (
    f"""
    CREATE TABLE IF NOT EXISTS {SECURITY_MASTER_SNAPSHOTS_TABLE} (
        snapshot_id TEXT PRIMARY KEY,
        retrieved_at TEXT NOT NULL,
        source_date TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        record_count INTEGER NOT NULL,
        status TEXT NOT NULL,
        payload TEXT NOT NULL
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {SECURITY_MASTER_RECORDS_TABLE} (
        snapshot_id TEXT NOT NULL,
        listing_id TEXT NOT NULL,
        isin TEXT NOT NULL,
        mic TEXT NOT NULL,
        exchange TEXT NOT NULL,
        trading_symbol TEXT NOT NULL,
        company_name TEXT NOT NULL,
        payload TEXT NOT NULL,
        PRIMARY KEY (snapshot_id, listing_id)
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {SECURITY_MASTER_CURRENT_TABLE} (
        pointer_key TEXT PRIMARY KEY,
        snapshot_id TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
)

_POSTGRES_DDL = (
    f"ALTER TABLE {SECURITY_MASTER_RECORDS_TABLE} "
    f"ADD COLUMN IF NOT EXISTS company_name TEXT NOT NULL DEFAULT ''",
    f"CREATE INDEX IF NOT EXISTS security_master_records_snapshot_symbol "
    f"ON {SECURITY_MASTER_RECORDS_TABLE} (snapshot_id, trading_symbol)",
    f"CREATE INDEX IF NOT EXISTS security_master_records_snapshot_isin "
    f"ON {SECURITY_MASTER_RECORDS_TABLE} (snapshot_id, isin)",
    f"CREATE INDEX IF NOT EXISTS security_master_records_snapshot_exchange "
    f"ON {SECURITY_MASTER_RECORDS_TABLE} (snapshot_id, exchange)",
    f"CREATE INDEX IF NOT EXISTS security_master_records_snapshot_name "
    f"ON {SECURITY_MASTER_RECORDS_TABLE} (snapshot_id, company_name)",
)


def _is_postgres(database: Any) -> bool:
    return type(database).__name__ == "PostgresDatabasePort"


class DatabaseSecurityMasterStore:
    def __init__(self, database: Any) -> None:
        self._db = database
        self._lock = Lock()
        self._current_cache: UniverseSnapshot | None = None
        self.ensure_schema()

    def ensure_schema(self) -> None:
        for stmt in _MIGRATIONS:
            self._db.execute(stmt.strip())
        if _is_postgres(self._db):
            for stmt in _POSTGRES_DDL:
                self._db.execute(stmt)

    def save_snapshot(self, snapshot: UniverseSnapshot) -> UniverseSnapshot:
        with self._lock:
            txn_factory = getattr(self._db, "transaction", None)
            if callable(txn_factory):
                with txn_factory() as txn:
                    if _is_postgres(self._db):
                        txn.execute(f"SELECT pg_advisory_xact_lock({_ADVISORY_LOCK_KEY})")
                    self._persist(txn, snapshot)
            else:
                self._persist(self._db, snapshot)
            if snapshot.status is not SnapshotStatus.FAILED:
                self._current_cache = snapshot
            return snapshot

    def current_snapshot(self) -> UniverseSnapshot | None:
        with self._lock:
            pointer = self._current_pointer()
            if not pointer:
                self._current_cache = None
                return None
            if self._current_cache is not None and self._current_cache.snapshot_id == pointer:
                return self._current_cache
            loaded = self._load_snapshot(pointer)
            self._current_cache = loaded
            return loaded

    def get_snapshot(self, snapshot_id: str) -> UniverseSnapshot | None:
        with self._lock:
            return self._load_snapshot(snapshot_id)

    def list_snapshots(self, *, limit: int = 20) -> tuple[dict[str, Any], ...]:
        with self._lock:
            current = self._current_pointer()
            rows: list[dict[str, Any]] = []
            for row in self._select(self._db, SECURITY_MASTER_SNAPSHOTS_TABLE):
                payload = decode_snapshot_payload(row.get("payload")) or {}
                rows.append(
                    {
                        "snapshot_id": row.get("snapshot_id"),
                        "retrieved_at": row.get("retrieved_at"),
                        "source_date": row.get("source_date"),
                        "content_hash": row.get("content_hash"),
                        "record_count": row.get("record_count"),
                        "status": row.get("status"),
                        "error": payload.get("error"),
                        "counts": payload.get("counts"),
                        "is_current": str(row.get("snapshot_id") or "") == current,
                    }
                )
            rows.sort(key=lambda item: str(item.get("retrieved_at") or ""), reverse=True)
            return tuple(rows[:limit])

    def _current_pointer(self) -> str:
        for row in self._select(self._db, SECURITY_MASTER_CURRENT_TABLE):
            if str(row.get("pointer_key") or "") == "CURRENT":
                return str(row.get("snapshot_id") or "")
        return ""

    def _persist(self, executor: Any, snapshot: UniverseSnapshot) -> None:
        existing = bool(
            self._select(
                executor, SECURITY_MASTER_SNAPSHOTS_TABLE, snapshot_id=snapshot.snapshot_id
            )
        )
        if not existing:
            self._insert_snapshot(executor, snapshot)
        if snapshot.status is not SnapshotStatus.FAILED:
            self._set_current(executor, snapshot.snapshot_id, snapshot.retrieved_at)

    def _insert_snapshot(self, executor: Any, snapshot: UniverseSnapshot) -> None:
        meta = snapshot.to_metadata_dict()
        encoded = encode_snapshot_payload(meta)
        executor.execute(
            f"INSERT INTO {SECURITY_MASTER_SNAPSHOTS_TABLE} "
            f"(snapshot_id, retrieved_at, source_date, content_hash, record_count, status, payload) VALUES ("
            f"{sql_literal(snapshot.snapshot_id)}, {sql_literal(snapshot.retrieved_at)}, "
            f"{sql_literal(snapshot.source_date)}, {sql_literal(snapshot.content_hash)}, "
            f"{sql_literal(snapshot.record_count)}, {sql_literal(str(snapshot.status))}, "
            f"{sql_literal(encoded)})"
        )
        if snapshot.status is SnapshotStatus.FAILED:
            return
        for record in snapshot.records:
            payload = encode_snapshot_payload(record.to_dict())
            executor.execute(
                f"INSERT INTO {SECURITY_MASTER_RECORDS_TABLE} "
                f"(snapshot_id, listing_id, isin, mic, exchange, trading_symbol, company_name, payload) VALUES ("
                f"{sql_literal(snapshot.snapshot_id)}, {sql_literal(record.listing_id)}, "
                f"{sql_literal(record.isin)}, {sql_literal(record.mic)}, "
                f"{sql_literal(record.exchange)}, {sql_literal(record.trading_symbol)}, "
                f"{sql_literal(record.company_name)}, {sql_literal(payload)})"
            )

    def _set_current(self, executor: Any, snapshot_id: str, updated_at: str) -> None:
        if _is_postgres(self._db):
            executor.execute(
                f"INSERT INTO {SECURITY_MASTER_CURRENT_TABLE} "
                f"(pointer_key, snapshot_id, updated_at) VALUES ("
                f"{sql_literal('CURRENT')}, {sql_literal(snapshot_id)}, {sql_literal(updated_at)}) "
                f"ON CONFLICT (pointer_key) DO UPDATE SET "
                f"snapshot_id = EXCLUDED.snapshot_id, updated_at = EXCLUDED.updated_at"
            )
            return
        executor.execute(
            f"DELETE FROM {SECURITY_MASTER_CURRENT_TABLE} WHERE pointer_key = 'CURRENT'"
        )
        executor.execute(
            f"INSERT INTO {SECURITY_MASTER_CURRENT_TABLE} "
            f"(pointer_key, snapshot_id, updated_at) VALUES ("
            f"{sql_literal('CURRENT')}, {sql_literal(snapshot_id)}, {sql_literal(updated_at)})"
        )

    def _load_snapshot(self, snapshot_id: str) -> UniverseSnapshot | None:
        key = snapshot_id.strip()
        if not key:
            return None
        meta = None
        for row in self._select(self._db, SECURITY_MASTER_SNAPSHOTS_TABLE, snapshot_id=key):
            meta = row
            break
        if meta is None:
            return None
        payload = decode_snapshot_payload(meta.get("payload")) or {}
        records = []
        for row in self._select(self._db, SECURITY_MASTER_RECORDS_TABLE, snapshot_id=key):
            item = decode_snapshot_payload(row.get("payload"))
            if isinstance(item, dict):
                records.append(record_from_dict(item))
        sources = tuple(
            SourceTrace(
                source_id=str(item.get("source_id") or ""),
                exchange=str(item.get("exchange") or ""),
                document_kind=str(item.get("document_kind") or ""),
                uri=str(item.get("uri") or ""),
                retrieved_at=str(item.get("retrieved_at") or ""),
                source_date=str(item.get("source_date") or "UNKNOWN"),
                content_hash=str(item.get("content_hash") or ""),
                record_count=int(item.get("record_count") or 0),
                status=str(item.get("status") or ""),
                last_modified=str(item.get("last_modified") or ""),
                error=str(item.get("error") or ""),
            )
            for item in (payload.get("sources") or [])
            if isinstance(item, dict)
        )
        counts_raw = payload.get("counts") if isinstance(payload.get("counts"), dict) else {}
        counts = UniverseCounts(
            **{key_name: int(counts_raw.get(key_name) or 0) for key_name in empty_counts().to_dict()}
        )
        try:
            status = SnapshotStatus(str(meta.get("status") or payload.get("status") or "ACCEPTED"))
        except ValueError:
            status = SnapshotStatus.FAILED
        return UniverseSnapshot(
            snapshot_id=key,
            retrieved_at=str(meta.get("retrieved_at") or ""),
            source_date=str(meta.get("source_date") or "UNKNOWN"),
            content_hash=str(meta.get("content_hash") or ""),
            record_count=int(meta.get("record_count") or len(records)),
            status=status,
            sources=tuple(sources),
            counts=counts,
            records=tuple(records),
            error=str(payload.get("error") or ""),
        )

    def _select(
        self,
        executor: Any,
        table: str,
        *,
        snapshot_id: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM {table}"
        if snapshot_id:
            sql += f" WHERE snapshot_id = {sql_literal(snapshot_id)}"
        rows = list(executor.fetchall(sql))
        if snapshot_id:
            return [row for row in rows if str(row.get("snapshot_id") or "") == snapshot_id]
        return rows
