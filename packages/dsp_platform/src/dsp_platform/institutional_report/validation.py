"""Validate Institutional Research Report structure (EPIC-R002)."""

from __future__ import annotations

from dsp_platform.institutional_report.models import (
    REPORT_SCHEMA_VERSION,
    REPORT_SECTION_ORDER,
    InstitutionalResearchReport,
    ReportSection,
)

__all__ = [
    "InstitutionalReportValidationError",
    "validate_institutional_report",
]


class InstitutionalReportValidationError(ValueError):
    """Report failed structural / RS section validation."""


_ALLOWED_STATUS = frozenset({"ok", "unavailable", "partial"})
_CONTENT_SECTIONS = tuple(s for s in REPORT_SECTION_ORDER if s not in {"metadata"})

# RS-001…RS-010 must each map to a present report section
_RS_REQUIRED = {
    "RS-001": "executive_summary",
    "RS-002": "market_data",
    "RS-003": "financial_statements",
    "RS-004": "valuation",
    "RS-005": "margin_of_safety",
    "RS-006": "business_quality",
    "RS-007": "risk",
    "RS-008": "scenarios",
    "RS-009": "explainability",
    "RS-010": "audit",
}


def _validate_section(section: ReportSection, expected_name: str) -> None:
    if section.name != expected_name:
        raise InstitutionalReportValidationError(
            f"section name mismatch: expected {expected_name!r}, got {section.name!r}"
        )
    if section.status not in _ALLOWED_STATUS:
        raise InstitutionalReportValidationError(
            f"section {expected_name!r} has invalid status {section.status!r}"
        )
    if section.available and section.payload is None:
        raise InstitutionalReportValidationError(
            f"section {expected_name!r} marked available with null payload"
        )
    if not section.available and section.payload is not None:
        raise InstitutionalReportValidationError(
            f"section {expected_name!r} has payload but marked unavailable"
        )
    if section.available and section.message == "Data unavailable.":
        raise InstitutionalReportValidationError(
            f"section {expected_name!r} available with unavailable message"
        )


def validate_institutional_report(report: InstitutionalResearchReport) -> None:
    """Reject structurally invalid reports. Never invents replacements."""
    if report.version.schema_version != REPORT_SCHEMA_VERSION:
        raise InstitutionalReportValidationError(
            f"unsupported schema_version {report.version.schema_version!r}"
        )
    if not report.metadata.report_id or not str(report.metadata.report_id).strip():
        raise InstitutionalReportValidationError("missing report_id")
    if not report.metadata.generated_at:
        raise InstitutionalReportValidationError("missing generated_at")
    if not report.metadata.research_object_id:
        raise InstitutionalReportValidationError("missing research_object_id")
    if not report.metadata.research_mode:
        raise InstitutionalReportValidationError("missing research_mode")

    for name in _CONTENT_SECTIONS:
        _validate_section(report.section(name), name)

    for rs_id, section_name in _RS_REQUIRED.items():
        section = report.section(section_name)
        if section.rs_id != rs_id:
            raise InstitutionalReportValidationError(
                f"{section_name} must carry rs_id={rs_id!r}, got {section.rs_id!r}"
            )

    if report.provenance is None:
        raise InstitutionalReportValidationError("missing provenance")
    if report.research_object_ref is None:
        raise InstitutionalReportValidationError("missing research_object_ref")
