"""Institutional Research Report (EPIC-R002) — Research Object projection only."""

from __future__ import annotations

from dsp_platform.institutional_report.generator import (
    GENERATOR_VERSION,
    InstitutionalReportGenerator,
    generate_institutional_report,
)
from dsp_platform.institutional_report.mapper import (
    field_or_unavailable,
    map_display_fields,
    section_payload_dict,
)
from dsp_platform.institutional_report.models import (
    REPORT_SCHEMA_VERSION,
    REPORT_SECTION_ORDER,
    UNAVAILABLE_MESSAGE,
    InstitutionalResearchReport,
    ReportMetadata,
    ReportSection,
    ReportVersion,
    freeze_mapping,
    utc_now,
)
from dsp_platform.institutional_report.serde import (
    institutional_report_from_dict,
    institutional_report_to_dict,
)
from dsp_platform.institutional_report.validation import (
    InstitutionalReportValidationError,
    validate_institutional_report,
)

__all__ = [
    "GENERATOR_VERSION",
    "REPORT_SCHEMA_VERSION",
    "REPORT_SECTION_ORDER",
    "UNAVAILABLE_MESSAGE",
    "InstitutionalReportGenerator",
    "InstitutionalReportValidationError",
    "InstitutionalResearchReport",
    "ReportMetadata",
    "ReportSection",
    "ReportVersion",
    "field_or_unavailable",
    "freeze_mapping",
    "generate_institutional_report",
    "institutional_report_from_dict",
    "institutional_report_to_dict",
    "map_display_fields",
    "section_payload_dict",
    "utc_now",
    "validate_institutional_report",
]
