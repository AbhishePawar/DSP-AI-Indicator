"""Platform façade helpers for Institutional Export (EPIC-R003)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_export import (
    EXPORT_FORMATS,
    EXPORT_SCHEMA_VERSION,
    export_artifact_to_dict,
    export_institutional_report,
)
from dsp_platform.institutional_report.models import REPORT_SCHEMA_VERSION

__all__ = [
    "export_canonical_institutional_report",
    "institutional_export_schema",
]


def institutional_export_schema() -> dict[str, Any]:
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exporter_version": "1.0.0",
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "immutable": True,
        "read_only": True,
        "source": "institutional_report",
        "formats": list(EXPORT_FORMATS),
    }


def export_canonical_institutional_report(
    report: Mapping[str, Any],
    *,
    format: str = "json",
    export_id: str | None = None,
    exported_at: str | None = None,
) -> dict[str, Any]:
    """Export an Institutional Report dict; returns serializable artifact."""
    artifact = export_institutional_report(
        report,
        format=format,
        export_id=export_id,
        exported_at=exported_at,
    )
    return export_artifact_to_dict(artifact)
