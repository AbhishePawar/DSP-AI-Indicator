"""Serialize committee reports (EPIC-A005)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from dsp_platform.institutional_committee.models import (
    COMMITTEE_SCHEMA_VERSION,
    COMMITTEE_SERVICE_VERSION,
    AgentReview,
    CommitteeReport,
    freeze_mapping_or_empty,
)
from dsp_platform.institutional_committee.validation import (
    InstitutionalCommitteeValidationError,
    validate_committee_report,
)

__all__ = [
    "committee_report_from_dict",
    "committee_report_to_dict",
]


def committee_report_to_dict(report: CommitteeReport) -> dict[str, Any]:
    validate_committee_report(report)
    return report.to_dict()


def committee_report_from_dict(data: Mapping[str, Any]) -> CommitteeReport:
    if not isinstance(data, Mapping):
        raise InstitutionalCommitteeValidationError("report must be a mapping")

    def mapping_field(source: Mapping[str, Any], name: str) -> Mapping[str, Any]:
        value = source.get(name)
        return value if isinstance(value, Mapping) else {}

    reviews: list[AgentReview] = []
    for row in data.get("reviews") or []:
        if not isinstance(row, Mapping):
            continue
        citations = tuple(
            freeze_mapping_or_empty(dict(c)) or freeze_mapping_or_empty({})
            for c in (row.get("citations") or [])
            if isinstance(c, Mapping)
        )
        findings = row.get("findings") or ()
        focus = row.get("focus_sections") or ()
        reviews.append(
            AgentReview(
                agent_id=str(row.get("agent_id") or ""),
                agent_name=str(row.get("agent_name") or ""),
                stance=str(row.get("stance") or ""),
                confidence=str(row.get("confidence") or ""),
                summary=str(row.get("summary") or ""),
                findings=tuple(findings) if isinstance(findings, (list, tuple)) else (),
                focus_sections=tuple(focus) if isinstance(focus, (list, tuple)) else (),
                citations=citations,
                provenance=freeze_mapping_or_empty(mapping_field(row, "provenance")),
            )
        )

    minority = tuple(
        freeze_mapping_or_empty(dict(m)) or freeze_mapping_or_empty({})
        for m in (data.get("minority_opinions") or [])
        if isinstance(m, Mapping)
    )
    citations = tuple(
        freeze_mapping_or_empty(dict(c)) or freeze_mapping_or_empty({})
        for c in (data.get("citations") or [])
        if isinstance(c, Mapping)
    )
    limitations = data.get("limitations") or ()
    report = CommitteeReport(
        report_id=str(data.get("report_id") or ""),
        schema_version=str(data.get("schema_version") or COMMITTEE_SCHEMA_VERSION),
        service_version=str(data.get("service_version") or COMMITTEE_SERVICE_VERSION),
        created_at=str(data.get("created_at") or ""),
        subject=str(data.get("subject") or ""),
        context=freeze_mapping_or_empty(mapping_field(data, "context")),
        reviews=tuple(reviews),
        consensus=freeze_mapping_or_empty(mapping_field(data, "consensus")),
        minority_opinions=minority,
        committee_summary=freeze_mapping_or_empty(mapping_field(data, "committee_summary")),
        citations=citations,
        provenance=freeze_mapping_or_empty(mapping_field(data, "provenance")),
        audit=freeze_mapping_or_empty(mapping_field(data, "audit")),
        limitations=(
            tuple(limitations) if isinstance(limitations, (list, tuple)) else ()
        ),
    )
    validate_committee_report(report)
    return report
