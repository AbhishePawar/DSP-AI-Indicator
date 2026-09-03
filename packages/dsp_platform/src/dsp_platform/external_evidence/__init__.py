"""Validated external research evidence package (AI web-research input).

Provider-neutral and calculation-neutral. Not a DSP data port.
"""

from __future__ import annotations

from dsp_platform.external_evidence.builder import (
    build_validated_external_evidence_package,
    empty_external_evidence_package,
)
from dsp_platform.external_evidence.models import (
    CANONICAL_CALCULATION_FACT_IDS,
    CURRENT_OUTSTANDING_FACT_IDS,
    EXTERNAL_EVIDENCE_SCHEMA_VERSION,
    PRIVATE_EVIDENCE_FIELD_NAMES,
    SEARCH_SNIPPET_SOURCE_TYPES,
    WEIGHTED_AVERAGE_SHARES_FACT_IDS,
    EvidenceKind,
    EvidenceQuality,
    EvidenceValidationStatus,
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
    ExternalEvidenceValidationError,
    QualitativeEvidenceTopic,
    SourceTier,
    SourceType,
    ValidatedExternalEvidencePackage,
)
from dsp_platform.external_evidence.validation import (
    assert_identities_compatible,
    is_search_snippet_source,
    normalize_identity_token,
    validate_external_evidence_identity,
    validate_external_evidence_record,
)

__all__ = [
    "CANONICAL_CALCULATION_FACT_IDS",
    "CURRENT_OUTSTANDING_FACT_IDS",
    "EXTERNAL_EVIDENCE_SCHEMA_VERSION",
    "PRIVATE_EVIDENCE_FIELD_NAMES",
    "SEARCH_SNIPPET_SOURCE_TYPES",
    "WEIGHTED_AVERAGE_SHARES_FACT_IDS",
    "EvidenceKind",
    "EvidenceQuality",
    "EvidenceValidationStatus",
    "ExternalEvidenceIdentity",
    "ExternalEvidenceRecord",
    "ExternalEvidenceValidationError",
    "QualitativeEvidenceTopic",
    "SourceTier",
    "SourceType",
    "ValidatedExternalEvidencePackage",
    "assert_identities_compatible",
    "build_validated_external_evidence_package",
    "empty_external_evidence_package",
    "is_search_snippet_source",
    "normalize_identity_token",
    "validate_external_evidence_identity",
    "validate_external_evidence_record",
]
