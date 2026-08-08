"""Serialize monitoring results (EPIC-A003)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_monitoring.models import (
    MONITORING_SCHEMA_VERSION,
    MONITORING_SERVICE_VERSION,
    MonitoringAlert,
    MonitoringEvaluateResult,
    SnapshotTrack,
    freeze_mapping,
)
from dsp_platform.research_monitoring.validation import (
    ResearchMonitoringValidationError,
    validate_monitoring_result,
)

__all__ = [
    "monitoring_result_from_dict",
    "monitoring_result_to_dict",
]


def monitoring_result_to_dict(result: MonitoringEvaluateResult) -> dict[str, Any]:
    validate_monitoring_result(result)
    return result.to_dict()


def monitoring_result_from_dict(data: Mapping[str, Any]) -> MonitoringEvaluateResult:
    if not isinstance(data, Mapping):
        raise ResearchMonitoringValidationError("result must be a mapping")
    tracks_raw = data.get("tracks") or []
    tracks: list[SnapshotTrack] = []
    if isinstance(tracks_raw, list):
        for row in tracks_raw:
            if not isinstance(row, Mapping):
                continue
            tracks.append(
                SnapshotTrack(
                    subject=str(row.get("subject") or ""),
                    subject_kind=str(row.get("subject_kind") or "symbol"),
                    baseline_snapshot_id=row.get("baseline_snapshot_id"),
                    current_snapshot_id=row.get("current_snapshot_id"),
                    tracked_at=str(row.get("tracked_at") or ""),
                )
            )
    alerts_raw = data.get("alerts") or []
    alerts: list[MonitoringAlert] = []
    if isinstance(alerts_raw, list):
        for row in alerts_raw:
            if not isinstance(row, Mapping):
                continue
            citations = tuple(
                freeze_mapping(dict(c)) or freeze_mapping({})
                for c in (row.get("citations") or [])
                if isinstance(c, Mapping)
            )
            alerts.append(
                MonitoringAlert(
                    alert_id=str(row.get("alert_id") or ""),
                    severity=str(row.get("severity") or ""),
                    subject=str(row.get("subject") or ""),
                    subject_kind=str(row.get("subject_kind") or ""),
                    alert_type=str(row.get("alert_type") or ""),
                    message=str(row.get("message") or ""),
                    citations=citations,
                    diff_id=row.get("diff_id"),
                    baseline_snapshot_id=row.get("baseline_snapshot_id"),
                    current_snapshot_id=row.get("current_snapshot_id"),
                    change_summary=freeze_mapping(
                        dict(row.get("change_summary") or {})
                    )
                    or freeze_mapping({}),
                    provenance=freeze_mapping(dict(row.get("provenance") or {}))
                    or freeze_mapping({}),
                )
            )
    limitations = data.get("limitations") or ()
    result = MonitoringEvaluateResult(
        result_id=str(data.get("result_id") or ""),
        schema_version=str(data.get("schema_version") or MONITORING_SCHEMA_VERSION),
        service_version=str(
            data.get("service_version") or MONITORING_SERVICE_VERSION
        ),
        created_at=str(data.get("created_at") or ""),
        watchlist=freeze_mapping(dict(data.get("watchlist") or {}))
        or freeze_mapping({}),
        portfolios=freeze_mapping(dict(data.get("portfolios") or {}))
        or freeze_mapping({}),
        tracks=tuple(tracks),
        alerts=tuple(alerts),
        provenance=freeze_mapping(dict(data.get("provenance") or {}))
        or freeze_mapping({}),
        audit=freeze_mapping(dict(data.get("audit") or {})) or freeze_mapping({}),
        limitations=tuple(limitations)
        if isinstance(limitations, (list, tuple))
        else (),
    )
    validate_monitoring_result(result)
    return result
