"""Build a ValidatedExternalEvidencePackage from structurally valid records.

Aggregator only: no web search, no LLM, no vendor adapters, no DSP engines.
"""

from __future__ import annotations

from collections.abc import Sequence

from dsp_platform.external_evidence.models import (
    EXTERNAL_EVIDENCE_SCHEMA_VERSION,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    SourceTier,
    ValidatedExternalEvidencePackage,
)
from dsp_platform.external_evidence.validation import (
    assert_identities_compatible,
    is_search_snippet_source,
    validate_external_evidence_identity,
    validate_external_evidence_record,
)

__all__ = [
    "build_validated_external_evidence_package",
    "empty_external_evidence_package",
]


def empty_external_evidence_package(
    subject: ExternalEvidenceIdentity,
) -> ValidatedExternalEvidencePackage:
    """Backward-compatible empty package — no external evidence attached."""
    return ValidatedExternalEvidencePackage(
        schema_version=EXTERNAL_EVIDENCE_SCHEMA_VERSION,
        subject=subject,
        records=(),
    )


def build_validated_external_evidence_package(
    records: Sequence[ExternalEvidenceRecord],
    *,
    subject: ExternalEvidenceIdentity,
) -> ValidatedExternalEvidencePackage:
    """Admit only structurally valid, validated, non-authoritative evidence."""
    if not isinstance(subject, ExternalEvidenceIdentity):
        raise ExternalEvidenceValidationError("package subject identity is required")
    validate_external_evidence_identity(subject)

    admitted: list[ExternalEvidenceRecord] = []
    seen_ids: set[str] = set()
    for record in records:
        validate_external_evidence_record(record)
        if record.validation_status is EvidenceValidationStatus.CANDIDATE:
            raise ExternalEvidenceValidationError(
                "candidate evidence cannot enter a validated evidence package"
            )
        if record.validation_status is EvidenceValidationStatus.REJECTED:
            raise ExternalEvidenceValidationError(
                "rejected evidence cannot enter a validated evidence package"
            )
        if record.validation_status is not EvidenceValidationStatus.VALIDATED:
            raise ExternalEvidenceValidationError(
                "validated package requires validation_status=validated"
            )
        if record.source_tier is SourceTier.TIER_3_DISCOVERY:
            raise ExternalEvidenceValidationError(
                "Tier 3 discovery cannot become authoritative evidence"
            )
        if is_search_snippet_source(record.source_type):
            raise ExternalEvidenceValidationError(
                "search-result snippets cannot be stored as "
                "authoritative source documents"
            )
        assert_identities_compatible(subject, record.identity)
        if record.fact_id in seen_ids:
            raise ExternalEvidenceValidationError(
                f"duplicate fact_id in validated package: {record.fact_id!r}"
            )
        seen_ids.add(record.fact_id)
        admitted.append(record)

    return ValidatedExternalEvidencePackage(
        schema_version=EXTERNAL_EVIDENCE_SCHEMA_VERSION,
        subject=subject,
        records=tuple(admitted),
    )
