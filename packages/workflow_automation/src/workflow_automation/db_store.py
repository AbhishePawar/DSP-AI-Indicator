"""DatabasePort-backed Workflow Automation store (RC1 Milestone 5).

One JSON snapshot row per user containing their alert rules, scheduled
reports, **and** notifications. Unlike ``portfolio_store``'s transaction
ledger (truly append-only, never mutated), a Notification's ``read_at``
*is* mutated after creation — and the shared ``InMemoryDatabasePort`` test
adapter's minimal SQL dialect supports only ``CREATE TABLE`` / ``INSERT
INTO`` / ``DELETE FROM`` (whole-table) / ``SELECT`` (no ``UPDATE``, no
row-scoped ``DELETE``). So notifications are stored in the same
rewrite-on-each-flush JSON snapshot as alert rules/scheduled reports,
rather than a separate append-only table — the correct data-store choice
for a mutable field, not a limitation being worked around. Uses
``InMemoryDatabasePort``'s dialect and any real
``production_platform.DatabasePort`` implementation identically — no import
dependency on ``production_platform`` is added (duck-typed, same convention
as ``portfolio_store.db_store`` / ``enterprise.db_store``).
"""

from __future__ import annotations

import base64
import json
from threading import Lock
from typing import Any

from workflow_automation.models import (
    AlertRule,
    Notification,
    ScheduledReport,
    freeze_mapping,
    utc_now,
)
from workflow_automation.store import InMemoryWorkflowAutomationStore

__all__ = [
    "WORKFLOW_AUTOMATION_MIGRATIONS_SQL",
    "DatabaseWorkflowAutomationStore",
    "build_workflow_automation_store",
]

WORKFLOW_AUTOMATION_MIGRATIONS_SQL = (
    """
    CREATE TABLE IF NOT EXISTS workflow_automation_snapshots (
        user_id TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
)


class DatabaseWorkflowAutomationStore(InMemoryWorkflowAutomationStore):
    """Workflow Automation store hydrated from / flushed to a ``DatabasePort``."""

    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self.ensure_schema()
        self.hydrate()

    def ensure_schema(self) -> None:
        for stmt in WORKFLOW_AUTOMATION_MIGRATIONS_SQL:
            self._db.execute(stmt.strip())

    def hydrate(self) -> None:
        rows = self._db.fetchall("SELECT * FROM workflow_automation_snapshots")
        alert_rules: dict[str, AlertRule] = {}
        scheduled_reports: dict[str, ScheduledReport] = {}
        notifications: dict[str, Notification] = {}
        for row in rows:
            raw = row.get("payload")
            payload = raw if isinstance(raw, dict) else _decode_payload(str(raw or ""))
            if not payload:
                continue
            for rid, rdata in (payload.get("alert_rules") or {}).items():
                alert_rules[rid] = _alert_rule_from_dict(rdata)
            for sid, sdata in (payload.get("scheduled_reports") or {}).items():
                scheduled_reports[sid] = _scheduled_report_from_dict(sdata)
            for nid, ndata in (payload.get("notifications") or {}).items():
                notifications[nid] = _notification_from_dict(ndata)
        with self._lock:
            self.alert_rules = alert_rules
            self.scheduled_reports = scheduled_reports
            self.notifications = notifications

    def flush(self) -> None:
        """Persist the full working set — one snapshot row per user."""
        with self._persist_lock:
            with self._lock:
                alert_rules = dict(self.alert_rules)
                scheduled_reports = dict(self.scheduled_reports)
                notifications = dict(self.notifications)

            by_user_rules: dict[str, dict[str, Any]] = {}
            for rid, rule in alert_rules.items():
                by_user_rules.setdefault(rule.user_id, {})[rid] = rule.to_dict()
            by_user_schedules: dict[str, dict[str, Any]] = {}
            for sid, schedule in scheduled_reports.items():
                by_user_schedules.setdefault(schedule.user_id, {})[sid] = (
                    schedule.to_dict()
                )
            by_user_notifications: dict[str, dict[str, Any]] = {}
            for nid, notification in notifications.items():
                by_user_notifications.setdefault(notification.user_id, {})[nid] = (
                    notification.to_dict()
                )

            user_ids = (
                set(by_user_rules) | set(by_user_schedules) | set(by_user_notifications)
            )

            # InMemoryDatabasePort DELETE clears the whole table — rewrite
            # every snapshot row on each flush (matches portfolio_store).
            self._db.execute("DELETE FROM workflow_automation_snapshots")
            now = utc_now().isoformat()
            for user_id in user_ids:
                snapshot = {
                    "alert_rules": by_user_rules.get(user_id, {}),
                    "scheduled_reports": by_user_schedules.get(user_id, {}),
                    "notifications": by_user_notifications.get(user_id, {}),
                }
                encoded = base64.b64encode(
                    json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
                ).decode("ascii")
                self._db.execute(
                    "INSERT INTO workflow_automation_snapshots "
                    "(user_id, payload, updated_at) VALUES "
                    f"({_sql_literal(user_id)}, {_sql_literal(encoded)}, "
                    f"{_sql_literal(now)})"
                )

    def clear(self) -> None:
        super().clear()
        with self._persist_lock:
            self._db.execute("DELETE FROM workflow_automation_snapshots")


def build_workflow_automation_store(
    database: Any | None = None,
) -> InMemoryWorkflowAutomationStore:
    """Factory — ``DatabasePort``-backed when provided, else in-memory."""
    if database is None:
        return InMemoryWorkflowAutomationStore()
    return DatabaseWorkflowAutomationStore(database)


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _decode_payload(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        decoded = base64.b64decode(raw.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _alert_rule_from_dict(data: dict[str, Any]) -> AlertRule:
    return AlertRule(
        rule_id=str(data["rule_id"]),
        user_id=str(data["user_id"]),
        rule_type=str(data["rule_type"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        symbol=data.get("symbol"),
        portfolio_id=data.get("portfolio_id"),
        active=bool(data.get("active", True)),
        params=freeze_mapping(data.get("params")),
        last_evaluated_at=data.get("last_evaluated_at"),
        last_status=data.get("last_status"),
    )


def _scheduled_report_from_dict(data: dict[str, Any]) -> ScheduledReport:
    return ScheduledReport(
        schedule_id=str(data["schedule_id"]),
        user_id=str(data["user_id"]),
        portfolio_id=str(data["portfolio_id"]),
        frequency=str(data["frequency"]),
        format=str(data["format"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        active=bool(data.get("active", True)),
        recipients=tuple(data.get("recipients") or ()),
        last_run_at=data.get("last_run_at"),
    )


def _notification_from_dict(data: dict[str, Any]) -> Notification:
    return Notification(
        notification_id=str(data["notification_id"]),
        user_id=str(data["user_id"]),
        kind=str(data["kind"]),
        title=str(data["title"]),
        message=str(data["message"]),
        created_at=str(data["created_at"]),
        related_rule_id=data.get("related_rule_id"),
        related_schedule_id=data.get("related_schedule_id"),
        read_at=data.get("read_at"),
    )
