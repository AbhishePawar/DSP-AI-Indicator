"""DatabasePort-backed share-research store.

Filesystem research candidates are ephemeral on Cloud Run. Promoted JSON
snapshots shipped in the image remain read-only packaged evidence. Runtime
CURRENT overlay and research history must survive instance restart, so they
live on the same DatabasePort already used for investment provenance.

History rows are append-only. Current rows are replaced by ISIN without
mutating archived history.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from dsp_platform.durable_snapshot import decode_snapshot_payload, encode_snapshot_payload, sql_literal
from dsp_platform.share_research.models import ShareResearchRecord
from dsp_platform.share_research.store import record_from_dict

__all__ = [
    "SHARE_RESEARCH_CURRENT_TABLE",
    "SHARE_RESEARCH_HISTORY_TABLE",
    "SHARE_RESEARCH_MIGRATIONS_SQL",
    "DatabaseShareResearchStore",
]

SHARE_RESEARCH_CURRENT_TABLE = "share_research_current"
SHARE_RESEARCH_HISTORY_TABLE = "share_research_history"

SHARE_RESEARCH_MIGRATIONS_SQL = (
    f"""
    CREATE TABLE IF NOT EXISTS {SHARE_RESEARCH_CURRENT_TABLE} (
        isin TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        research_id TEXT NOT NULL,
        status TEXT NOT NULL,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS {SHARE_RESEARCH_HISTORY_TABLE} (
        history_id TEXT PRIMARY KEY,
        isin TEXT NOT NULL,
        research_id TEXT NOT NULL,
        status TEXT NOT NULL,
        payload TEXT NOT NULL,
        archived_at TEXT NOT NULL
    )
    """,
)


class DatabaseShareResearchStore:
    """Durable share-research current + append-only history."""

    def __init__(self, database: Any) -> None:
        self._db = database
        self._lock = Lock()
        self.ensure_schema()

    def ensure_schema(self) -> None:
        for stmt in SHARE_RESEARCH_MIGRATIONS_SQL:
            self._db.execute(stmt.strip())

    def load_current(self, isin: str) -> ShareResearchRecord | None:
        key = isin.strip().upper()
        if not key:
            return None
        for row in self._db.fetchall(f"SELECT * FROM {SHARE_RESEARCH_CURRENT_TABLE}"):
            if str(row.get("isin") or "").strip().upper() != key:
                continue
            payload = decode_snapshot_payload(row.get("payload"))
            if not isinstance(payload, dict):
                return None
            return record_from_dict(payload)
        return None

    def load_history(self, isin: str, *, limit: int = 20) -> tuple[dict[str, Any], ...]:
        key = isin.strip().upper()
        rows: list[dict[str, Any]] = []
        for row in self._db.fetchall(f"SELECT * FROM {SHARE_RESEARCH_HISTORY_TABLE}"):
            if str(row.get("isin") or "").strip().upper() != key:
                continue
            payload = decode_snapshot_payload(row.get("payload"))
            if not isinstance(payload, dict):
                continue
            rows.append(
                {
                    "research_id": payload.get("research_id") or row.get("research_id"),
                    "status": payload.get("status") or row.get("status"),
                    "outstanding_shares": payload.get("outstanding_shares"),
                    "as_of": payload.get("as_of"),
                    "current_through": payload.get("current_through"),
                    "last_verified_at": payload.get("last_verified_at"),
                    "researched_at": payload.get("researched_at"),
                    "archived_at": row.get("archived_at"),
                    "integrity_hash": payload.get("integrity_hash"),
                }
            )
        rows.sort(key=lambda item: str(item.get("archived_at") or ""), reverse=True)
        return tuple(rows[:limit])

    def save(self, record: ShareResearchRecord) -> None:
        isin = record.isin.strip().upper()
        with self._lock:
            previous = self.load_current(isin)
            if previous is not None:
                self._append_history(previous)
            self._replace_current(record)

    def _append_history(self, record: ShareResearchRecord) -> None:
        isin = record.isin.strip().upper()
        history_id = (
            f"{isin}_{record.research_id}_"
            f"{record.researched_at.strftime('%Y%m%dT%H%M%SZ')}"
        )
        existing = self._db.fetchall(f"SELECT * FROM {SHARE_RESEARCH_HISTORY_TABLE}")
        if any(str(row.get("history_id") or "") == history_id for row in existing):
            return
        encoded = encode_snapshot_payload(record.to_dict())
        archived_at = record.updated_at.isoformat()
        self._db.execute(
            f"INSERT INTO {SHARE_RESEARCH_HISTORY_TABLE} "
            f"(history_id, isin, research_id, status, payload, archived_at) VALUES ("
            f"{sql_literal(history_id)}, {sql_literal(isin)}, "
            f"{sql_literal(record.research_id)}, {sql_literal(str(record.status))}, "
            f"{sql_literal(encoded)}, {sql_literal(archived_at)})"
        )

    def _replace_current(self, record: ShareResearchRecord) -> None:
        isin = record.isin.strip().upper()
        encoded = encode_snapshot_payload(record.to_dict())
        updated = record.updated_at.isoformat()
        insert_sql = (
            f"INSERT INTO {SHARE_RESEARCH_CURRENT_TABLE} "
            f"(isin, ticker, research_id, status, payload, updated_at) VALUES ("
            f"{sql_literal(isin)}, {sql_literal(record.ticker)}, "
            f"{sql_literal(record.research_id)}, {sql_literal(str(record.status))}, "
            f"{sql_literal(encoded)}, {sql_literal(updated)})"
        )
        if type(self._db).__name__ == "InMemoryDatabasePort":
            rows = self._db.fetchall(f"SELECT * FROM {SHARE_RESEARCH_CURRENT_TABLE}")
            keep = [
                row
                for row in rows
                if str(row.get("isin") or "").strip().upper() != isin
            ]
            self._db.execute(f"DELETE FROM {SHARE_RESEARCH_CURRENT_TABLE}")
            for row in keep:
                self._db.execute(
                    f"INSERT INTO {SHARE_RESEARCH_CURRENT_TABLE} "
                    f"(isin, ticker, research_id, status, payload, updated_at) VALUES ("
                    f"{sql_literal(row.get('isin'))}, {sql_literal(row.get('ticker'))}, "
                    f"{sql_literal(row.get('research_id'))}, {sql_literal(row.get('status'))}, "
                    f"{sql_literal(row.get('payload'))}, {sql_literal(row.get('updated_at'))})"
                )
            self._db.execute(insert_sql)
            return
        self._db.execute(
            f"DELETE FROM {SHARE_RESEARCH_CURRENT_TABLE} WHERE isin = {sql_literal(isin)}"
        )
        self._db.execute(insert_sql)
