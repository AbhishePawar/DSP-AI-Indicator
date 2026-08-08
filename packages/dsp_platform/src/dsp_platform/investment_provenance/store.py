"""Append-only durable investment provenance store (P1-06 / G8)."""

from __future__ import annotations

import base64
import json
from threading import Lock
from typing import Any, Protocol

from dsp_platform.durable_snapshot import sql_literal
from dsp_platform.investment_provenance.models import InvestmentProvenanceRecord
from dsp_platform.investment_provenance.redaction import redact_secrets

__all__ = [
    "INVESTMENT_PROVENANCE_TABLE",
    "INVESTMENT_PROVENANCE_MIGRATIONS_SQL",
    "InvestmentProvenanceStore",
    "InMemoryInvestmentProvenanceStore",
    "DatabaseInvestmentProvenanceStore",
    "InvestmentProvenanceError",
    "InvestmentProvenanceForbidden",
    "get_investment_provenance_store",
    "configure_investment_provenance_store",
    "reset_investment_provenance_store_for_tests",
]

INVESTMENT_PROVENANCE_TABLE = "investment_analysis_provenance"

INVESTMENT_PROVENANCE_MIGRATIONS_SQL = (
    f"""
    CREATE TABLE IF NOT EXISTS {INVESTMENT_PROVENANCE_TABLE} (
        analysis_id TEXT PRIMARY KEY,
        ticker TEXT NOT NULL,
        company TEXT,
        exchange TEXT,
        correlation_id TEXT,
        owner_user_id TEXT,
        org_id TEXT,
        created_at TEXT NOT NULL,
        payload TEXT NOT NULL,
        input_fingerprint TEXT,
        result_fingerprint TEXT,
        immutable INTEGER NOT NULL
    )
    """,
)


class InvestmentProvenanceError(RuntimeError):
    """Durable provenance persistence or retrieval failure."""


class InvestmentProvenanceForbidden(PermissionError):
    """Tenant isolation denial for provenance access."""


class InvestmentProvenanceStore(Protocol):
    def append(self, record: InvestmentProvenanceRecord) -> InvestmentProvenanceRecord:
        ...

    def get(
        self,
        analysis_id: str,
        *,
        actor_user_id: str | None = None,
        org_id: str | None = None,
    ) -> InvestmentProvenanceRecord | None:
        ...

    def list_by_ticker(
        self,
        ticker: str,
        *,
        actor_user_id: str | None = None,
        org_id: str | None = None,
        limit: int = 50,
    ) -> list[InvestmentProvenanceRecord]:
        ...

    def ensure_fresh(self) -> None:
        ...


class InMemoryInvestmentProvenanceStore:
    """Process-local append-only store — tests / non-durable fallback only."""

    def __init__(self) -> None:
        self._rows: dict[str, InvestmentProvenanceRecord] = {}
        self._lock = Lock()

    def append(self, record: InvestmentProvenanceRecord) -> InvestmentProvenanceRecord:
        with self._lock:
            if record.analysis_id in self._rows:
                raise InvestmentProvenanceError(
                    f"analysis_id already exists (append-only): {record.analysis_id}"
                )
            self._rows[record.analysis_id] = record
            return record

    def get(
        self,
        analysis_id: str,
        *,
        actor_user_id: str | None = None,
        org_id: str | None = None,
    ) -> InvestmentProvenanceRecord | None:
        with self._lock:
            record = self._rows.get(str(analysis_id))
        if record is None:
            return None
        _enforce_tenant(record, actor_user_id=actor_user_id, org_id=org_id)
        return record

    def list_by_ticker(
        self,
        ticker: str,
        *,
        actor_user_id: str | None = None,
        org_id: str | None = None,
        limit: int = 50,
    ) -> list[InvestmentProvenanceRecord]:
        key = ticker.strip().upper()
        with self._lock:
            rows = [r for r in self._rows.values() if r.ticker == key]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        out: list[InvestmentProvenanceRecord] = []
        for record in rows:
            try:
                _enforce_tenant(record, actor_user_id=actor_user_id, org_id=org_id)
            except InvestmentProvenanceForbidden:
                continue
            out.append(record)
            if len(out) >= limit:
                break
        return out

    def ensure_fresh(self) -> None:
        return None


class DatabaseInvestmentProvenanceStore:
    """DatabasePort-backed append-only investment provenance (P0-06 pattern)."""

    def __init__(self, database: Any) -> None:
        self._db = database
        self._lock = Lock()
        self.ensure_schema()

    def ensure_schema(self) -> None:
        for stmt in INVESTMENT_PROVENANCE_MIGRATIONS_SQL:
            self._db.execute(stmt.strip())

    def ensure_fresh(self) -> None:
        """No process cache — every read hits DatabasePort."""
        return None

    def append(self, record: InvestmentProvenanceRecord) -> InvestmentProvenanceRecord:
        safe = redact_secrets(record.to_dict())
        payload = _b64_json(safe)
        cols = (
            "analysis_id, ticker, company, exchange, correlation_id, owner_user_id, "
            "org_id, created_at, payload, input_fingerprint, result_fingerprint, immutable"
        )
        vals = ", ".join(
            [
                sql_literal(record.analysis_id),
                sql_literal(record.ticker),
                sql_literal(record.company),
                sql_literal(record.exchange),
                sql_literal(record.correlation_id),
                sql_literal(record.owner_user_id),
                sql_literal(record.org_id),
                sql_literal(record.created_at),
                sql_literal(payload),
                sql_literal(record.input_fingerprint),
                sql_literal(record.result_fingerprint),
                "1",
            ]
        )
        with self._lock:
            existing = self._db.fetchall(
                f"SELECT * FROM {INVESTMENT_PROVENANCE_TABLE}"
            )
            if any(str(r.get("analysis_id")) == record.analysis_id for r in existing):
                raise InvestmentProvenanceError(
                    f"analysis_id already exists (append-only): {record.analysis_id}"
                )
            try:
                self._db.execute(
                    f"INSERT INTO {INVESTMENT_PROVENANCE_TABLE} ({cols}) "
                    f"VALUES ({vals})"
                )
            except Exception as exc:  # noqa: BLE001
                raise InvestmentProvenanceError(
                    f"failed to persist investment provenance: {exc}"
                ) from exc
        return record

    def get(
        self,
        analysis_id: str,
        *,
        actor_user_id: str | None = None,
        org_id: str | None = None,
    ) -> InvestmentProvenanceRecord | None:
        rows = self._db.fetchall(f"SELECT * FROM {INVESTMENT_PROVENANCE_TABLE}")
        for row in rows:
            if str(row.get("analysis_id")) != str(analysis_id):
                continue
            record = _record_from_row(row)
            _enforce_tenant(record, actor_user_id=actor_user_id, org_id=org_id)
            return record
        return None

    def list_by_ticker(
        self,
        ticker: str,
        *,
        actor_user_id: str | None = None,
        org_id: str | None = None,
        limit: int = 50,
    ) -> list[InvestmentProvenanceRecord]:
        key = ticker.strip().upper()
        rows = self._db.fetchall(f"SELECT * FROM {INVESTMENT_PROVENANCE_TABLE}")
        matched = [
            _record_from_row(r)
            for r in rows
            if str(r.get("ticker") or "").upper() == key
        ]
        matched.sort(key=lambda r: r.created_at, reverse=True)
        out: list[InvestmentProvenanceRecord] = []
        for record in matched:
            try:
                _enforce_tenant(record, actor_user_id=actor_user_id, org_id=org_id)
            except InvestmentProvenanceForbidden:
                continue
            out.append(record)
            if len(out) >= limit:
                break
        return out


_STORE: InvestmentProvenanceStore | None = None
_STORE_LOCK = Lock()


def configure_investment_provenance_store(
    database: Any | None = None,
) -> InvestmentProvenanceStore:
    """Wire durable store when DatabasePort is present."""
    global _STORE
    with _STORE_LOCK:
        if database is not None and all(
            hasattr(database, name) for name in ("execute", "fetchall", "ping")
        ):
            _STORE = DatabaseInvestmentProvenanceStore(database)
        else:
            _STORE = InMemoryInvestmentProvenanceStore()
        return _STORE


def get_investment_provenance_store() -> InvestmentProvenanceStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = InMemoryInvestmentProvenanceStore()
        return _STORE


def reset_investment_provenance_store_for_tests(
    store: InvestmentProvenanceStore | None = None,
) -> InvestmentProvenanceStore:
    global _STORE
    with _STORE_LOCK:
        _STORE = store if store is not None else InMemoryInvestmentProvenanceStore()
        return _STORE


def _enforce_tenant(
    record: InvestmentProvenanceRecord,
    *,
    actor_user_id: str | None,
    org_id: str | None,
) -> None:
    """P1-07 inheritance — owned records require matching actor/org."""
    owner = (record.owner_user_id or "").strip()
    record_org = (record.org_id or "").strip()
    actor = (actor_user_id or "").strip()
    req_org = (org_id or "").strip()

    if not owner and not record_org:
        # Unowned research-path records: readable without tenant stamp.
        return

    if record_org:
        if not req_org or req_org != record_org:
            raise InvestmentProvenanceForbidden(
                "cross-tenant investment provenance access denied"
            )
        return

    if owner and owner != actor:
        raise InvestmentProvenanceForbidden(
            "investment provenance owner mismatch"
        )


def _b64_json(value: dict[str, Any]) -> str:
    return base64.b64encode(
        json.dumps(value, separators=(",", ":"), default=str).encode("utf-8")
    ).decode("ascii")


def _decode_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str) or not raw:
        return {}
    try:
        decoded = base64.b64decode(raw.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:  # noqa: BLE001
            return {}


def _record_from_row(row: dict[str, Any]) -> InvestmentProvenanceRecord:
    payload = _decode_payload(row.get("payload"))
    if not payload.get("analysis_id"):
        payload["analysis_id"] = row.get("analysis_id")
    if not payload.get("created_at"):
        payload["created_at"] = row.get("created_at")
    if not payload.get("ticker"):
        payload["ticker"] = row.get("ticker")
    return InvestmentProvenanceRecord.from_dict(payload)
