"""Optional duck-typed SQL persistence for compliance stores (PEP-004).

Accepts any DatabasePort-shaped object (PEP-002) without importing
production_platform — keeps architecture boundaries intact.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from compliance.audit import AuditEvent
from compliance.consent import ConsentRecord
from compliance.recommendation_history import RecommendationHistoryEntry
from compliance.research_archive import ArchivedResearch

__all__ = [
    "SqlAuditPort",
    "SqlConsentPort",
    "SqlRecommendationHistoryPort",
    "SqlResearchArchivePort",
    "ensure_compliance_schema",
]


_SCHEMA = (
    """
    CREATE TABLE IF NOT EXISTS compliance_consents (
        consent_id TEXT PRIMARY KEY,
        subject_id TEXT,
        purpose_id TEXT,
        granted INTEGER,
        policy_version TEXT,
        recorded_at TEXT,
        locale TEXT,
        channel TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS compliance_history (
        entry_id TEXT PRIMARY KEY,
        symbol TEXT,
        action_label TEXT,
        issued_at TEXT,
        horizon TEXT,
        target_price TEXT,
        report_ref TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS compliance_archive (
        archive_id TEXT PRIMARY KEY,
        report_ref TEXT,
        archived_at TEXT,
        retention_class TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS compliance_audit (
        event_id TEXT PRIMARY KEY,
        action TEXT,
        actor TEXT,
        occurred_at TEXT,
        resource_ref TEXT,
        detail TEXT
    )
    """,
)


def ensure_compliance_schema(database: Any) -> None:
    for stmt in _SCHEMA:
        database.execute(stmt.strip())


def _lit(value: Any) -> str:
    if value is None:
        return "''"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


class SqlConsentPort:
    """ConsentPort over duck-typed DatabasePort."""

    def __init__(self, database: Any, *, policy: Any = None) -> None:
        from compliance.consent import default_consent_policy

        self._db = database
        self._policy = policy or default_consent_policy()
        ensure_compliance_schema(database)

    def current_policy(self):
        return self._policy

    def record(self, consent: ConsentRecord) -> ConsentRecord:
        self._db.execute(
            "INSERT INTO compliance_consents ("
            "consent_id, subject_id, purpose_id, granted, policy_version, "
            "recorded_at, locale, channel"
            ") VALUES ("
            f"{_lit(consent.consent_id)}, {_lit(consent.subject_id)}, "
            f"{_lit(consent.purpose_id)}, {_lit(1 if consent.granted else 0)}, "
            f"{_lit(consent.policy_version)}, {_lit(consent.recorded_at.isoformat())}, "
            f"{_lit(consent.locale)}, {_lit(consent.channel)}"
            ")"
        )
        return consent

    def list_for_subject(self, subject_id: str) -> tuple[ConsentRecord, ...]:
        rows = self._db.fetchall("SELECT * FROM compliance_consents")
        out: list[ConsentRecord] = []
        for row in rows:
            if str(row.get("subject_id")) != subject_id:
                continue
            out.append(
                ConsentRecord(
                    consent_id=str(row["consent_id"]),
                    subject_id=str(row["subject_id"]),
                    purpose_id=str(row["purpose_id"]),
                    granted=bool(int(row.get("granted", 0))),
                    policy_version=str(row["policy_version"]),
                    recorded_at=datetime.fromisoformat(str(row["recorded_at"])),
                    locale=str(row.get("locale") or "en-IN"),
                    channel=str(row.get("channel") or "app"),
                )
            )
        return tuple(out)

    def latest_for_purpose(self, subject_id: str, purpose_id: str) -> ConsentRecord | None:
        matches = [
            c
            for c in self.list_for_subject(subject_id)
            if c.purpose_id == purpose_id
        ]
        return matches[-1] if matches else None

    def withdraw(self, subject_id: str, purpose_id: str, *, policy_version: str) -> ConsentRecord:
        import uuid

        rec = ConsentRecord(
            consent_id=f"cns_{uuid.uuid4().hex[:12]}",
            subject_id=subject_id,
            purpose_id=purpose_id,
            granted=False,
            policy_version=policy_version,
        )
        return self.record(rec)


class SqlRecommendationHistoryPort:
    def __init__(self, database: Any) -> None:
        self._db = database
        ensure_compliance_schema(database)

    def append(self, entry: RecommendationHistoryEntry) -> None:
        self._db.execute(
            "INSERT INTO compliance_history ("
            "entry_id, symbol, action_label, issued_at, horizon, target_price, report_ref"
            ") VALUES ("
            f"{_lit(entry.entry_id)}, {_lit(entry.symbol)}, {_lit(entry.action_label)}, "
            f"{_lit(entry.issued_at.isoformat())}, {_lit(entry.horizon)}, "
            f"{_lit(entry.target_price)}, {_lit(entry.report_ref)}"
            ")"
        )

    def list_for_symbol(self, symbol: str) -> tuple[RecommendationHistoryEntry, ...]:
        key = symbol.strip().upper()
        rows = self._db.fetchall("SELECT * FROM compliance_history")
        out: list[RecommendationHistoryEntry] = []
        for row in rows:
            if str(row.get("symbol", "")).upper() != key:
                continue
            horizon = str(row.get("horizon") or "") or None
            target_price = str(row.get("target_price") or "") or None
            report_ref = str(row.get("report_ref") or "") or None
            out.append(
                RecommendationHistoryEntry(
                    entry_id=str(row["entry_id"]),
                    symbol=str(row["symbol"]),
                    action_label=str(row["action_label"]),
                    issued_at=datetime.fromisoformat(str(row["issued_at"])),
                    horizon=horizon,
                    target_price=target_price,
                    report_ref=report_ref,
                )
            )
        return tuple(out)


class SqlResearchArchivePort:
    def __init__(self, database: Any) -> None:
        self._db = database
        ensure_compliance_schema(database)

    def archive(self, report_ref: str) -> ArchivedResearch:
        import uuid

        item = ArchivedResearch(
            archive_id=f"ra_{uuid.uuid4().hex[:12]}",
            report_ref=report_ref,
            archived_at=datetime.now(tz=UTC),
            retention_class="research_standard",
        )
        self._db.execute(
            "INSERT INTO compliance_archive ("
            "archive_id, report_ref, archived_at, retention_class"
            ") VALUES ("
            f"{_lit(item.archive_id)}, {_lit(item.report_ref)}, "
            f"{_lit(item.archived_at.isoformat())}, {_lit(item.retention_class)}"
            ")"
        )
        return item

    def get(self, archive_id: str) -> ArchivedResearch:
        rows = self._db.fetchall("SELECT * FROM compliance_archive")
        for row in rows:
            if str(row.get("archive_id")) == archive_id:
                return ArchivedResearch(
                    archive_id=str(row["archive_id"]),
                    report_ref=str(row["report_ref"]),
                    archived_at=datetime.fromisoformat(str(row["archived_at"])),
                    retention_class=str(row.get("retention_class") or "standard"),
                )
        raise KeyError(archive_id)


class SqlAuditPort:
    def __init__(self, database: Any) -> None:
        self._db = database
        ensure_compliance_schema(database)

    def record(self, event: AuditEvent) -> None:
        self._db.execute(
            "INSERT INTO compliance_audit ("
            "event_id, action, actor, occurred_at, resource_ref, detail"
            ") VALUES ("
            f"{_lit(event.event_id)}, {_lit(event.action)}, {_lit(event.actor)}, "
            f"{_lit(event.occurred_at.isoformat())}, {_lit(event.resource_ref)}, "
            f"{_lit(event.detail)}"
            ")"
        )

    def list_for_resource(self, resource_ref: str) -> tuple[AuditEvent, ...]:
        rows = self._db.fetchall("SELECT * FROM compliance_audit")
        out: list[AuditEvent] = []
        for row in rows:
            if str(row.get("resource_ref")) != resource_ref:
                continue
            out.append(
                AuditEvent(
                    event_id=str(row["event_id"]),
                    action=str(row["action"]),
                    actor=str(row["actor"]),
                    occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
                    resource_ref=str(row.get("resource_ref") or "") or None,
                    detail=str(row.get("detail") or "") or None,
                )
            )
        return tuple(out)
