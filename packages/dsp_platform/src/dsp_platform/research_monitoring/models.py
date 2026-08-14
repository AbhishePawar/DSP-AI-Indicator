"""Continuous Research Monitoring models (EPIC-A003)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "ALERT_SEVERITIES",
    "MONITORING_SCHEMA_VERSION",
    "MONITORING_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "MonitoringAlert",
    "MonitoringEvaluateResult",
    "SnapshotTrack",
    "freeze_mapping",
    "utc_now",
]

MONITORING_SCHEMA_VERSION = "1.0.0"
MONITORING_SERVICE_VERSION = "1.0.0"
ALERT_SEVERITIES = ("info", "watch", "important", "unavailable")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class SnapshotTrack:
    subject: str  # symbol or portfolio_id
    subject_kind: str  # symbol | portfolio
    baseline_snapshot_id: str | None
    current_snapshot_id: str | None
    tracked_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "subject_kind": self.subject_kind,
            "baseline_snapshot_id": self.baseline_snapshot_id,
            "current_snapshot_id": self.current_snapshot_id,
            "tracked_at": self.tracked_at,
        }


@dataclass(frozen=True, slots=True)
class MonitoringAlert:
    alert_id: str
    severity: str
    subject: str
    subject_kind: str
    alert_type: str
    message: str
    citations: tuple[Mapping[str, Any], ...]
    diff_id: str | None = None
    baseline_snapshot_id: str | None = None
    current_snapshot_id: str | None = None
    change_summary: Mapping[str, Any] = field(default_factory=dict)
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "alert_id": self.alert_id,
            "severity": self.severity,
            "subject": self.subject,
            "subject_kind": self.subject_kind,
            "alert_type": self.alert_type,
            "message": self.message,
            "citations": [_plain(c) for c in self.citations],
            "diff_id": self.diff_id,
            "baseline_snapshot_id": self.baseline_snapshot_id,
            "current_snapshot_id": self.current_snapshot_id,
            "change_summary": _plain(self.change_summary),
            "provenance": _plain(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class MonitoringEvaluateResult:
    result_id: str
    schema_version: str
    service_version: str
    created_at: str
    watchlist: Mapping[str, Any]
    portfolios: Mapping[str, Any]
    tracks: tuple[SnapshotTrack, ...]
    alerts: tuple[MonitoringAlert, ...]
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
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "watchlist": _plain(self.watchlist),
            "portfolios": _plain(self.portfolios),
            "tracks": [t.to_dict() for t in self.tracks],
            "alerts": [a.to_dict() for a in self.alerts],
            "provenance": _plain(self.provenance),
            "audit": _plain(self.audit),
            "limitations": list(self.limitations),
        }
