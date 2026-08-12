"""Platform façade helpers for Institutional Research Report (EPIC-R002)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_report import (
    REPORT_SCHEMA_VERSION,
    REPORT_SECTION_ORDER,
    generate_institutional_report,
    institutional_report_to_dict,
)
from dsp_platform.research_object.models import RESEARCH_OBJECT_SCHEMA_VERSION

__all__ = [
    "generate_canonical_institutional_report",
    "institutional_report_schema",
]


def institutional_report_schema() -> dict[str, Any]:
    """Static schema descriptor for discovery endpoints."""
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generator_version": "1.0.0",
        "research_object_schema_version": RESEARCH_OBJECT_SCHEMA_VERSION,
        "immutable": True,
        "read_only": True,
        "source": "research_object",
        "sections": list(REPORT_SECTION_ORDER),
        "rs_coverage": [
            "RS-001",
            "RS-002",
            "RS-003",
            "RS-004",
            "RS-005",
            "RS-006",
            "RS-007",
            "RS-008",
            "RS-009",
            "RS-010",
        ],
    }


def generate_canonical_institutional_report(
    research_object: Mapping[str, Any],
    *,
    report_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Generate and serialize a report from a Research Object dict only."""
    report = generate_institutional_report(
        research_object,
        report_id=report_id,
        generated_at=generated_at,
    )
    return institutional_report_to_dict(report)
