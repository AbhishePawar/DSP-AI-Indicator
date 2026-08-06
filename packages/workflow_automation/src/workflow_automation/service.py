"""Workflow Automation persistence service (RC1 Milestone 5).

Ownership-checked CRUD over ``WorkflowAutomationStorePort``. No market data,
valuation, or evaluation logic lives here — see ``evaluation.py`` for the
pure comparison functions and ``dsp_platform.workflow_automation`` for the
orchestration that supplies them with already-computed signals. Mirrors
``portfolio_store.service.PortfolioService``'s structure exactly (store
abstraction + singleton factory + explicit ``flush()`` after each mutation).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from workflow_automation.enums import AlertRuleType, ScheduleFormat, ScheduleFrequency
from workflow_automation.exceptions import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from workflow_automation.models import (
    WORKFLOW_AUTOMATION_SCHEMA_VERSION,
    WORKFLOW_AUTOMATION_SERVICE_VERSION,
    AlertRule,
    Notification,
    ScheduledReport,
    freeze_mapping,
    utc_now,
)
from workflow_automation.ports import WorkflowAutomationStorePort
from workflow_automation.store import InMemoryWorkflowAutomationStore

__all__ = [
    "WorkflowAutomationService",
    "get_workflow_automation_service",
    "reset_workflow_automation_service_for_tests",
]

_ALERT_RULE_TYPES = tuple(t.value for t in AlertRuleType)
_SCHEDULE_FREQUENCIES = tuple(f.value for f in ScheduleFrequency)
_SCHEDULE_FORMATS = tuple(f.value for f in ScheduleFormat)


class WorkflowAutomationService:
    """Server-side ownership store for Alert Rules / Scheduled Reports /
    Notifications."""

    def __init__(
        self,
        store: WorkflowAutomationStorePort
        | InMemoryWorkflowAutomationStore
        | None = None,
    ) -> None:
        self.store: WorkflowAutomationStorePort = (
            store or InMemoryWorkflowAutomationStore()
        )

    # ------------------------------------------------------------------ schema
    def schema(self) -> dict[str, Any]:
        return {
            "schema_version": WORKFLOW_AUTOMATION_SCHEMA_VERSION,
            "service_version": WORKFLOW_AUTOMATION_SERVICE_VERSION,
            "alert_rule_types": list(_ALERT_RULE_TYPES),
            "schedule_frequencies": list(_SCHEDULE_FREQUENCIES),
            "schedule_formats": list(_SCHEDULE_FORMATS),
            "capabilities": [
                "alert_rule_crud",
                "scheduled_report_crud",
                "notification_center",
                "durable_store_when_database_port_supplied",
            ],
            "rules": [
                "every_resource_owned_by_authenticated_user",
                "no_market_data_no_valuation_in_this_package",
                "earnings_upcoming_always_unavailable_no_calendar_source",
                "no_autonomous_scheduler_run_now_only",
            ],
        }

    # --------------------------------------------------------------- ownership
    def _get_owned_rule(self, rule_id: str, *, user_id: str) -> AlertRule:
        rule = self.store.alert_rules.get(rule_id)
        if rule is None:
            raise NotFoundError(f"alert rule not found: {rule_id}")
        if rule.user_id != user_id:
            raise ForbiddenError("not the owner of this alert rule")
        return rule

    def _get_owned_schedule(self, schedule_id: str, *, user_id: str) -> ScheduledReport:
        schedule = self.store.scheduled_reports.get(schedule_id)
        if schedule is None:
            raise NotFoundError(f"scheduled report not found: {schedule_id}")
        if schedule.user_id != user_id:
            raise ForbiddenError("not the owner of this scheduled report")
        return schedule

    def _get_owned_notification(
        self, notification_id: str, *, user_id: str
    ) -> Notification:
        notification = self.store.notifications.get(notification_id)
        if notification is None:
            raise NotFoundError(f"notification not found: {notification_id}")
        if notification.user_id != user_id:
            raise ForbiddenError("not the owner of this notification")
        return notification

    # -------------------------------------------------------------- alert rules
    def create_alert_rule(
        self,
        *,
        user_id: str,
        rule_type: str,
        symbol: str | None = None,
        portfolio_id: str | None = None,
        params: Mapping[str, Any] | None = None,
        active: bool = True,
        rule_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip()
        if not uid:
            raise ValidationError("user_id required")
        clean_type = str(rule_type or "").strip().lower()
        if clean_type not in _ALERT_RULE_TYPES:
            raise ValidationError(
                f"invalid rule_type {rule_type!r}; expected one of {_ALERT_RULE_TYPES}"
            )
        symbol_required_types = (
            "price_above",
            "price_below",
            "valuation_flip",
            "earnings_upcoming",
            "research_stale",
        )
        if clean_type in symbol_required_types and not symbol:
            raise ValidationError(f"symbol required for rule_type {clean_type!r}")
        rid = (rule_id or f"alr_{uuid.uuid4().hex[:16]}").strip()
        if rid in self.store.alert_rules:
            raise ValidationError("rule_id already exists")
        now = created_at or utc_now().isoformat()
        rule = AlertRule(
            rule_id=rid,
            user_id=uid,
            rule_type=clean_type,
            created_at=now,
            updated_at=now,
            symbol=(symbol.strip().upper() if symbol else None),
            portfolio_id=portfolio_id,
            active=bool(active),
            params=freeze_mapping(params),
        )
        self.store.alert_rules[rid] = rule
        self.store.flush()
        return rule.to_dict()

    def list_alert_rules(
        self, *, user_id: str, active_only: bool = False
    ) -> list[dict[str, Any]]:
        rows = [r for r in self.store.alert_rules.values() if r.user_id == user_id]
        if active_only:
            rows = [r for r in rows if r.active]
        rows.sort(key=lambda r: r.created_at, reverse=True)
        return [r.to_dict() for r in rows]

    def get_alert_rule(self, rule_id: str, *, user_id: str) -> dict[str, Any]:
        return self._get_owned_rule(rule_id, user_id=user_id).to_dict()

    def update_alert_rule(
        self,
        rule_id: str,
        *,
        user_id: str,
        active: bool | None = None,
        params: Mapping[str, Any] | None = None,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        rule = self._get_owned_rule(rule_id, user_id=user_id)
        updated = _replace_rule(
            rule,
            active=bool(active) if active is not None else rule.active,
            params=freeze_mapping(params) if params is not None else rule.params,
            updated_at=updated_at or utc_now().isoformat(),
        )
        self.store.alert_rules[rule_id] = updated
        self.store.flush()
        return updated.to_dict()

    def record_alert_evaluation(
        self,
        rule_id: str,
        *,
        user_id: str,
        status: str,
        evaluated_at: str | None = None,
    ) -> dict[str, Any]:
        rule = self._get_owned_rule(rule_id, user_id=user_id)
        updated = _replace_rule(
            rule,
            last_status=status,
            last_evaluated_at=evaluated_at or utc_now().isoformat(),
        )
        self.store.alert_rules[rule_id] = updated
        self.store.flush()
        return updated.to_dict()

    def delete_alert_rule(self, rule_id: str, *, user_id: str) -> bool:
        self._get_owned_rule(rule_id, user_id=user_id)
        del self.store.alert_rules[rule_id]
        self.store.flush()
        return True

    # ---------------------------------------------------------- scheduled reports
    def create_scheduled_report(
        self,
        *,
        user_id: str,
        portfolio_id: str,
        frequency: str,
        format: str = "json",
        recipients: list[str] | None = None,
        active: bool = True,
        schedule_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip()
        if not uid:
            raise ValidationError("user_id required")
        if not portfolio_id:
            raise ValidationError("portfolio_id required")
        clean_frequency = str(frequency or "").strip().lower()
        if clean_frequency not in _SCHEDULE_FREQUENCIES:
            raise ValidationError(
                f"invalid frequency {frequency!r}; "
                f"expected one of {_SCHEDULE_FREQUENCIES}"
            )
        clean_format = str(format or "json").strip().lower()
        if clean_format not in _SCHEDULE_FORMATS:
            raise ValidationError(
                f"invalid format {format!r}; expected one of {_SCHEDULE_FORMATS}"
            )
        sid = (schedule_id or f"sch_{uuid.uuid4().hex[:16]}").strip()
        if sid in self.store.scheduled_reports:
            raise ValidationError("schedule_id already exists")
        now = created_at or utc_now().isoformat()
        schedule = ScheduledReport(
            schedule_id=sid,
            user_id=uid,
            portfolio_id=str(portfolio_id),
            frequency=clean_frequency,
            format=clean_format,
            created_at=now,
            updated_at=now,
            active=bool(active),
            recipients=tuple(recipients or ()),
        )
        self.store.scheduled_reports[sid] = schedule
        self.store.flush()
        return schedule.to_dict()

    def list_scheduled_reports(self, *, user_id: str) -> list[dict[str, Any]]:
        rows = [
            s for s in self.store.scheduled_reports.values() if s.user_id == user_id
        ]
        rows.sort(key=lambda s: s.created_at, reverse=True)
        return [s.to_dict() for s in rows]

    def get_scheduled_report(self, schedule_id: str, *, user_id: str) -> dict[str, Any]:
        return self._get_owned_schedule(schedule_id, user_id=user_id).to_dict()

    def update_scheduled_report(
        self,
        schedule_id: str,
        *,
        user_id: str,
        active: bool | None = None,
        frequency: str | None = None,
        format: str | None = None,
        recipients: list[str] | None = None,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        schedule = self._get_owned_schedule(schedule_id, user_id=user_id)
        new_frequency = schedule.frequency
        if frequency is not None:
            new_frequency = str(frequency).strip().lower()
            if new_frequency not in _SCHEDULE_FREQUENCIES:
                raise ValidationError(f"invalid frequency {frequency!r}")
        new_format = schedule.format
        if format is not None:
            new_format = str(format).strip().lower()
            if new_format not in _SCHEDULE_FORMATS:
                raise ValidationError(f"invalid format {format!r}")
        updated = _replace_schedule(
            schedule,
            active=bool(active) if active is not None else schedule.active,
            frequency=new_frequency,
            format=new_format,
            recipients=tuple(recipients)
            if recipients is not None
            else schedule.recipients,
            updated_at=updated_at or utc_now().isoformat(),
        )
        self.store.scheduled_reports[schedule_id] = updated
        self.store.flush()
        return updated.to_dict()

    def record_schedule_run(
        self, schedule_id: str, *, user_id: str, run_at: str | None = None
    ) -> dict[str, Any]:
        schedule = self._get_owned_schedule(schedule_id, user_id=user_id)
        updated = _replace_schedule(
            schedule, last_run_at=run_at or utc_now().isoformat()
        )
        self.store.scheduled_reports[schedule_id] = updated
        self.store.flush()
        return updated.to_dict()

    def delete_scheduled_report(self, schedule_id: str, *, user_id: str) -> bool:
        self._get_owned_schedule(schedule_id, user_id=user_id)
        del self.store.scheduled_reports[schedule_id]
        self.store.flush()
        return True

    # ------------------------------------------------------------- notifications
    def create_notification(
        self,
        *,
        user_id: str,
        kind: str,
        title: str,
        message: str,
        related_rule_id: str | None = None,
        related_schedule_id: str | None = None,
        notification_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip()
        if not uid:
            raise ValidationError("user_id required")
        nid = notification_id or f"ntf_{uuid.uuid4().hex[:16]}"
        notification = Notification(
            notification_id=nid,
            user_id=uid,
            kind=str(kind or "system"),
            title=str(title or ""),
            message=str(message or ""),
            created_at=created_at or utc_now().isoformat(),
            related_rule_id=related_rule_id,
            related_schedule_id=related_schedule_id,
        )
        self.store.notifications[nid] = notification
        self.store.flush()
        return notification.to_dict()

    def list_notifications(
        self, *, user_id: str, unread_only: bool = False, limit: int = 200
    ) -> list[dict[str, Any]]:
        rows = [n for n in self.store.notifications.values() if n.user_id == user_id]
        if unread_only:
            rows = [n for n in rows if n.read_at is None]
        rows.sort(key=lambda n: n.created_at, reverse=True)
        return [n.to_dict() for n in rows[: max(1, int(limit))]]

    def mark_notification_read(
        self, notification_id: str, *, user_id: str, read_at: str | None = None
    ) -> dict[str, Any]:
        notification = self._get_owned_notification(notification_id, user_id=user_id)
        updated = Notification(
            notification_id=notification.notification_id,
            user_id=notification.user_id,
            kind=notification.kind,
            title=notification.title,
            message=notification.message,
            created_at=notification.created_at,
            related_rule_id=notification.related_rule_id,
            related_schedule_id=notification.related_schedule_id,
            read_at=read_at or utc_now().isoformat(),
        )
        self.store.notifications[notification_id] = updated
        self.store.flush()
        return updated.to_dict()


def _replace_rule(rule: AlertRule, **changes: Any) -> AlertRule:
    data = rule.to_dict()
    data.update(changes)
    return AlertRule(
        rule_id=data["rule_id"],
        user_id=data["user_id"],
        rule_type=data["rule_type"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        symbol=data.get("symbol"),
        portfolio_id=data.get("portfolio_id"),
        active=data.get("active", True),
        params=freeze_mapping(data.get("params")),
        last_evaluated_at=data.get("last_evaluated_at"),
        last_status=data.get("last_status"),
    )


def _replace_schedule(schedule: ScheduledReport, **changes: Any) -> ScheduledReport:
    data = schedule.to_dict()
    data.update(changes)
    return ScheduledReport(
        schedule_id=data["schedule_id"],
        user_id=data["user_id"],
        portfolio_id=data["portfolio_id"],
        frequency=data["frequency"],
        format=data["format"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        active=data.get("active", True),
        recipients=tuple(data.get("recipients") or ()),
        last_run_at=data.get("last_run_at"),
    )


_SVC: WorkflowAutomationService | None = None


def get_workflow_automation_service(
    *, database: Any | None = None
) -> WorkflowAutomationService:
    """Return process singleton — durable store when a DatabasePort is supplied."""
    global _SVC
    if _SVC is None:
        store: WorkflowAutomationStorePort | None = None
        if database is not None:
            from workflow_automation.db_store import DatabaseWorkflowAutomationStore

            store = DatabaseWorkflowAutomationStore(database)
        _SVC = WorkflowAutomationService(store=store)
    return _SVC


def reset_workflow_automation_service_for_tests(
    service: WorkflowAutomationService | None = None,
) -> None:
    global _SVC
    _SVC = service
