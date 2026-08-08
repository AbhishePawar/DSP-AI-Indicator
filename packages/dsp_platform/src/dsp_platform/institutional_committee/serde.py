"""Serialize committee reports (EPIC-A005)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_committee.models import (
    COMMITTEE_SCHEMA_VERSION,
    COMMITTEE_SERVICE_VERSION,
    AgentReview,
    CommitteeReport,
    freeze_mapping,
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

    reviews: list[AgentReview] = []
    for row in data.get("reviews") or []:
        if not isinstance(row, Mapping):
            continue
        citations = tuple(
            freeze_mapping(dict(c)) or freeze_mapping({})
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
                findings=tuple(findings)
                if isinstance(findings, (list, tuple))
                else (),
                focus_sections=tuple(focus)
                if isinstance(focus, (list, tuple))
                else (),
                citations=citations,
                provenance=freeze_mapping(dict(row.get("provenance") or {}))
                or freeze_mapping({}),
            )
        )

    minority = tuple(
        freeze_mapping(dict(m)) or freeze_mapping({})
        for m in (data.get("minority_opinions") or [])
        if isinstance(m, Mapping)
    )
    citations = tuple(
        freeze_mapping(dict(c)) or freeze_mapping({})
        for c in (data.get("citations") or [])
        if isinstance(c, Mapping)
    )
    limitations = data.get("limitations") or ()
    report = CommitteeReport(
        report_id=str(data.get("report_id") or ""),
        schema_version=str(data.get("schema_version") or COMMITTEE_SCHEMA_VERSION),
        service_version=str(
            data.get("service_version") or COMMITTEE_SERVICE_VERSION
        ),
        created_at=str(data.get("created_at") or ""),
        subject=str(data.get("subject") or ""),
        context=freeze_mapping(dict(data.get("context") or {})) or freeze_mapping({}),
        reviews=tuple(reviews),
        consensus=freeze_mapping(dict(data.get("consensus") or {}))
        or freeze_mapping({}),
        minority_opinions=minority,
        committee_summary=freeze_mapping(dict(data.get("committee_summary") or {}))
        or freeze_mapping({}),
        citations=citations,
        provenance=freeze_mapping(dict(data.get("provenance") or {}))
        or freeze_mapping({}),
        audit=freeze_mapping(dict(data.get("audit") or {})) or freeze_mapping({}),
        limitations=tuple(limitations)
        if isinstance(limitations, (list, tuple))
        else (),
    )
    validate_committee_report(report)
    return report
