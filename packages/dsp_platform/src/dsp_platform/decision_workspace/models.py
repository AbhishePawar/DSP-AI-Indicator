"""Institutional Decision Workspace models (EPIC-A004)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "PANEL_NAMES",
    "UNAVAILABLE_MESSAGE",
    "WORKSPACE_KINDS",
    "WORKSPACE_SCHEMA_VERSION",
    "WORKSPACE_SERVICE_VERSION",
    "TimelineEvent",
    "WorkspacePanel",
    "WorkspaceResult",
    "freeze_mapping",
    "utc_now",
]

WORKSPACE_SCHEMA_VERSION = "1.0.0"
WORKSPACE_SERVICE_VERSION = "1.0.0"
WORKSPACE_KINDS = ("company", "portfolio", "watchlist")
PANEL_NAMES = (
    "research",
    "report",
    "timeline",
    "active_alerts",
    "report_history",
    "snapshot_history",
    "diff_history",
    "copilot",
    "portfolio",
    "monitoring",
    "audit",
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    event_id: str
    event_type: str
    timestamp: str
    label: str
    source_kind: str
    available: bool
    ref_id: str | None = None
    message: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "label": self.label,
            "source_kind": self.source_kind,
            "available": self.available,
            "ref_id": self.ref_id,
            "message": self.message,
            "metadata": _plain(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class WorkspacePanel:
    name: str
    available: bool
    status: str  # ok | unavailable | partial
    source_kind: str
    summary: Mapping[str, Any]
    citations: tuple[Mapping[str, Any], ...]
    payload: Mapping[str, Any] | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "name": self.name,
            "available": self.available,
            "status": self.status,
            "source_kind": self.source_kind,
            "summary": _plain(self.summary),
            "citations": [_plain(c) for c in self.citations],
            "payload": _plain(self.payload) if self.payload is not None else None,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceResult:
    workspace_id: str
    schema_version: str
    service_version: str
    created_at: str
    kind: str
    subject: str
    panels: tuple[WorkspacePanel, ...]
    timeline: tuple[TimelineEvent, ...]
    citations: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    audit: Mapping[str, Any]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "workspace_id": self.workspace_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "kind": self.kind,
            "subject": self.subject,
            "panels": [p.to_dict() for p in self.panels],
            "timeline": [e.to_dict() for e in self.timeline],
            "citations": [_plain(c) for c in self.citations],
            "provenance": _plain(self.provenance),
            "audit": _plain(self.audit),
            "limitations": list(self.limitations),
        }
