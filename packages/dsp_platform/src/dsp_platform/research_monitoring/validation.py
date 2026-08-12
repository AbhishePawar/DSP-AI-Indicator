"""Validate monitoring results (EPIC-A003)."""

from __future__ import annotations

from dsp_platform.research_monitoring.models import (
    ALERT_SEVERITIES,
    MONITORING_SCHEMA_VERSION,
    MonitoringEvaluateResult,
)

__all__ = [
    "ResearchMonitoringValidationError",
    "validate_monitoring_result",
]


class ResearchMonitoringValidationError(ValueError):
    """Monitoring result failed validation."""


def validate_monitoring_result(result: MonitoringEvaluateResult) -> None:
    if result.schema_version != MONITORING_SCHEMA_VERSION:
        raise ResearchMonitoringValidationError(
            f"unsupported schema_version {result.schema_version!r}"
        )
    if not result.result_id.strip():
        raise ResearchMonitoringValidationError("missing result_id")
    if not result.created_at:
        raise ResearchMonitoringValidationError("missing created_at")
    for alert in result.alerts:
        if alert.severity not in ALERT_SEVERITIES:
            raise ResearchMonitoringValidationError(
                f"invalid severity {alert.severity!r}"
            )
        if not alert.citations:
            raise ResearchMonitoringValidationError(
                f"alert {alert.alert_id} missing citations"
            )
        for citation in alert.citations:
            if not citation.get("path") or not citation.get("section"):
                raise ResearchMonitoringValidationError(
                    "citation missing path/section"
                )
    if result.provenance is None or result.audit is None:
        raise ResearchMonitoringValidationError("missing provenance/audit")
