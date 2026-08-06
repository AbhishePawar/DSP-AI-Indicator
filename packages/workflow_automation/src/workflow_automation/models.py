"""Workflow Automation persistence domain models (RC1 Milestone 5).

Frozen dataclasses only, mirroring ``portfolio_store.models`` conventions.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any

__all__ = [
    "WORKFLOW_AUTOMATION_SCHEMA_VERSION",
    "WORKFLOW_AUTOMATION_SERVICE_VERSION",
    "AlertRule",
    "Notification",
    "ScheduledReport",
    "freeze_mapping",
    "utc_now",
]

WORKFLOW_AUTOMATION_SCHEMA_VERSION = "1.0.0"
WORKFLOW_AUTOMATION_SERVICE_VERSION = "1.0.0"


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})

    def _freeze(obj: Any) -> Any:
        if isinstance(obj, Mapping):
            return MappingProxyType({str(k): _freeze(v) for k, v in obj.items()})
        if isinstance(obj, (list, tuple)):
            return tuple(_freeze(v) for v in obj)
        return obj

    return _freeze(value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class AlertRule:
    """A user-owned rule evaluated against an already-computed signal.

    ``params`` holds rule-type-specific fields (e.g. ``threshold_price`` for
    ``price_above``/``price_below``, ``watch_class`` for ``valuation_flip``,
    ``last_analysed_at``/``max_age_days`` for ``research_stale``) — kept as a
    generic mapping so new rule types never require a schema migration.
    """

    rule_id: str
    user_id: str
    rule_type: str
    created_at: str
    updated_at: str
    symbol: str | None = None
    portfolio_id: str | None = None
    active: bool = True
    params: Mapping[str, Any] = field(default_factory=dict)
    last_evaluated_at: str | None = None
    last_status: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "user_id": self.user_id,
            "rule_type": self.rule_type,
            "symbol": self.symbol,
            "portfolio_id": self.portfolio_id,
            "active": self.active,
            "params": dict(self.params),
            "last_evaluated_at": self.last_evaluated_at,
            "last_status": self.last_status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class ScheduledReport:
    """A user-owned scheduled-report/export *definition*.

    Recorded here is the declared cadence only — no cron/worker executes it
    autonomously (see package README "Remaining gaps"). ``run_now`` is the
    only implemented execution path.
    """

    schedule_id: str
    user_id: str
    portfolio_id: str
    frequency: str
    format: str
    created_at: str
    updated_at: str
    active: bool = True
    recipients: tuple[str, ...] = ()
    last_run_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schedule_id": self.schedule_id,
            "user_id": self.user_id,
            "portfolio_id": self.portfolio_id,
            "frequency": self.frequency,
            "format": self.format,
            "active": self.active,
            "recipients": list(self.recipients),
            "last_run_at": self.last_run_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True, slots=True)
class Notification:
    """One Notification Center entry — append-only, mutated only by ``read_at``."""

    notification_id: str
    user_id: str
    kind: str
    title: str
    message: str
    created_at: str
    related_rule_id: str | None = None
    related_schedule_id: str | None = None
    read_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "user_id": self.user_id,
            "kind": self.kind,
            "title": self.title,
            "message": self.message,
            "related_rule_id": self.related_rule_id,
            "related_schedule_id": self.related_schedule_id,
            "read_at": self.read_at,
            "created_at": self.created_at,
        }
