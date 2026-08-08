"""Immutable Research Snapshot Registry store (EPIC-011B).

Never overwrites. Prefer DatabasePort when available; InMemory for tests
and local development. Documented gap: full Postgres schema migration is
additive and optional behind the port.
"""

from __future__ import annotations

import json
from threading import RLock
from typing import Any, Protocol

from dsp_platform.research_intelligence.models import ResearchSnapshot

__all__ = [
    "DatabaseResearchSnapshotStore",
    "InMemoryResearchSnapshotStore",
    "ResearchSnapshotStore",
    "SnapshotAlreadyExistsError",
    "SnapshotNotFoundError",
    "ensure_snapshot_schema",
]


class SnapshotAlreadyExistsError(ValueError):
    """Refuses mutation of an existing research_id."""


class SnapshotNotFoundError(KeyError):
    """research_id not present in registry."""


class ResearchSnapshotStore(Protocol):
    def put_if_absent(self, snapshot: ResearchSnapshot) -> None: ...

    def get(self, research_id: str) -> ResearchSnapshot | None: ...

    def list_all(self) -> tuple[ResearchSnapshot, ...]: ...

    def list_by_symbol(self, symbol: str) -> tuple[ResearchSnapshot, ...]: ...

    def list_by_company(self, company: str) -> tuple[ResearchSnapshot, ...]: ...


class InMemoryResearchSnapshotStore:
    """Process-local immutable registry — overwrite is forbidden."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_id: dict[str, ResearchSnapshot] = {}

    def put_if_absent(self, snapshot: ResearchSnapshot) -> None:
        with self._lock:
            if snapshot.research_id in self._by_id:
                raise SnapshotAlreadyExistsError(
                    f"snapshot already registered: {snapshot.research_id}"
                )
            self._by_id[snapshot.research_id] = snapshot

    def get(self, research_id: str) -> ResearchSnapshot | None:
        with self._lock:
            return self._by_id.get(research_id)

    def list_all(self) -> tuple[ResearchSnapshot, ...]:
        with self._lock:
            snaps = list(self._by_id.values())
            snaps.sort(key=lambda s: s.timestamp)
            return tuple(snaps)

    def list_by_symbol(self, symbol: str) -> tuple[ResearchSnapshot, ...]:
        key = str(symbol).strip().upper()
        with self._lock:
            snaps = [
                s
                for s in self._by_id.values()
                if (s.symbol or "").upper() == key
            ]
            snaps.sort(key=lambda s: s.timestamp)
            return tuple(snaps)

    def list_by_company(self, company: str) -> tuple[ResearchSnapshot, ...]:
        key = str(company).strip().lower()
        with self._lock:
            snaps = [
                s
                for s in self._by_id.values()
                if (s.company or "").strip().lower() == key
            ]
            snaps.sort(key=lambda s: s.timestamp)
            return tuple(snaps)


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS research_intelligence_snapshots (
    research_id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL,
    symbol TEXT,
    company TEXT,
    timestamp TEXT NOT NULL,
    content_sha256 TEXT NOT NULL
)
"""


def ensure_snapshot_schema(db: Any) -> None:
    """Best-effort schema ensure on a DatabasePort-compatible object."""
    try:
        db.execute(_SCHEMA_SQL)
    except Exception:  # noqa: BLE001
        # Some adapters ignore DDL; caller may pre-provision.
        pass


def _row_to_snapshot(row: Mapping[str, Any]) -> ResearchSnapshot:
    raw = row.get("payload_json") or row.get("PAYLOAD_JSON")
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    data = json.loads(str(raw))
    return ResearchSnapshot(
        research_id=str(data["research_id"]),
        company=data.get("company"),
        exchange=data.get("exchange"),
        sector=data.get("sector"),
        industry=data.get("industry"),
        timestamp=str(data["timestamp"]),
        recommendation=data.get("recommendation"),
        confidence=data.get("confidence"),
        confidence_label=data.get("confidence_label"),
        intrinsic_value=data.get("intrinsic_value"),
        price=data.get("price"),
        margin_of_safety=data.get("margin_of_safety"),
        business_quality_score=data.get("business_quality_score"),
        management_score=data.get("management_score"),
        moat_score=data.get("moat_score"),
        risk_score=data.get("risk_score"),
        ai_committee_decision=data.get("ai_committee_decision"),
        explainability_summary=data.get("explainability_summary"),
        evidence_refs=tuple(data.get("evidence_refs") or ()),
        source_confidence=data.get("source_confidence"),
        research_version=data.get("research_version"),
        model_version=data.get("model_version"),
        content_sha256=str(data["content_sha256"]),
        symbol=data.get("symbol"),
        metadata=dict(data.get("metadata") or {}),
    )


class DatabaseResearchSnapshotStore:
    """Durable registry adapter over EPIC-011A DatabasePort.

    Stores frozen JSON payloads. Does not alter analytical tables.
    """

    def __init__(self, database: Any) -> None:
        self._db = database
        ensure_snapshot_schema(database)

    def put_if_absent(self, snapshot: ResearchSnapshot) -> None:
        existing = self.get(snapshot.research_id)
        if existing is not None:
            raise SnapshotAlreadyExistsError(
                f"snapshot already registered: {snapshot.research_id}"
            )
        payload = json.dumps(snapshot.to_dict(), sort_keys=True, default=str)
        self._db.execute(
            """
            INSERT INTO research_intelligence_snapshots
            (research_id, payload_json, symbol, company, timestamp, content_sha256)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.research_id,
                payload,
                snapshot.symbol,
                snapshot.company,
                snapshot.timestamp,
                snapshot.content_sha256,
            ),
        )

    def get(self, research_id: str) -> ResearchSnapshot | None:
        rows = self._db.fetchall(
            "SELECT payload_json FROM research_intelligence_snapshots "
            "WHERE research_id = ?",
            (research_id,),
        )
        if not rows:
            return None
        return _row_to_snapshot(rows[0])

    def list_all(self) -> tuple[ResearchSnapshot, ...]:
        rows = self._db.fetchall(
            "SELECT payload_json FROM research_intelligence_snapshots "
            "ORDER BY timestamp ASC"
        )
        return tuple(_row_to_snapshot(r) for r in rows)

    def list_by_symbol(self, symbol: str) -> tuple[ResearchSnapshot, ...]:
        key = str(symbol).strip().upper()
        rows = self._db.fetchall(
            "SELECT payload_json FROM research_intelligence_snapshots "
            "WHERE UPPER(symbol) = ? ORDER BY timestamp ASC",
            (key,),
        )
        return tuple(_row_to_snapshot(r) for r in rows)

    def list_by_company(self, company: str) -> tuple[ResearchSnapshot, ...]:
        key = str(company).strip().lower()
        rows = self._db.fetchall(
            "SELECT payload_json FROM research_intelligence_snapshots "
            "WHERE LOWER(company) = ? ORDER BY timestamp ASC",
            (key,),
        )
        return tuple(_row_to_snapshot(r) for r in rows)
