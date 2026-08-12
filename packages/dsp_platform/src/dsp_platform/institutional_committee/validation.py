"""Validate committee reports (EPIC-A005)."""

from __future__ import annotations

from dsp_platform.institutional_committee.models import (
    AGENT_IDS,
    COMMITTEE_SCHEMA_VERSION,
    CONFIDENCE_LEVELS,
    STANCES,
    CommitteeReport,
)

__all__ = [
    "InstitutionalCommitteeValidationError",
    "validate_committee_report",
]


class InstitutionalCommitteeValidationError(ValueError):
    """Committee report failed validation."""


def validate_committee_report(report: CommitteeReport) -> None:
    if report.schema_version != COMMITTEE_SCHEMA_VERSION:
        raise InstitutionalCommitteeValidationError(
            f"unsupported schema_version {report.schema_version!r}"
        )
    if not report.report_id.strip():
        raise InstitutionalCommitteeValidationError("missing report_id")
    if not report.subject.strip():
        raise InstitutionalCommitteeValidationError("missing subject")
    if not report.created_at:
        raise InstitutionalCommitteeValidationError("missing created_at")
    ids = [r.agent_id for r in report.reviews]
    if ids != list(AGENT_IDS):
        raise InstitutionalCommitteeValidationError(
            f"reviews must match AGENT_IDS order, got {ids!r}"
        )
    for review in report.reviews:
        if review.stance not in STANCES:
            raise InstitutionalCommitteeValidationError(
                f"invalid stance {review.stance!r}"
            )
        if review.confidence not in CONFIDENCE_LEVELS:
            raise InstitutionalCommitteeValidationError(
                f"invalid confidence {review.confidence!r}"
            )
        if not review.citations:
            raise InstitutionalCommitteeValidationError(
                f"agent {review.agent_id} missing citations"
            )
        for c in review.citations:
            if not c.get("path") or not c.get("section"):
                raise InstitutionalCommitteeValidationError(
                    f"agent {review.agent_id} citation missing path/section"
                )
    if not report.citations:
        raise InstitutionalCommitteeValidationError("committee citations required")
    if report.provenance is None or report.audit is None:
        raise InstitutionalCommitteeValidationError("missing provenance/audit")
    if not isinstance(report.consensus, dict) and report.consensus is not None:
        # MappingProxyType is Mapping — ok
        pass
    if "stance" not in report.consensus:
        raise InstitutionalCommitteeValidationError("consensus missing stance")
