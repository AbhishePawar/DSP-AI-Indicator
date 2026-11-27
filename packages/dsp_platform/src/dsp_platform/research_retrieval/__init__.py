"""Phase 7: Evidence-Based Hybrid Research Retrieval Layer for DSP-AI-Indicator."""

from __future__ import annotations

from dsp_platform.research_retrieval.deduplication import (
    DeduplicationEngine,
    DeduplicationResult,
    canonicalize_url,
)
from dsp_platform.research_retrieval.document_validator import (
    DocumentValidationResult,
    DocumentValidator,
    ValidationFailureReason,
    detect_prompt_injection,
    parse_indian_and_western_number,
)
from dsp_platform.research_retrieval.governance import (
    GovernanceDecision,
    RetrievalGovernance,
    is_approved_host,
    normalize_source_name,
)
from dsp_platform.research_retrieval.models import (
    ConflictingClaim,
    DiscoveredSource,
    EvidenceFreshness,
    EvidenceStatus,
    FetchedDocument,
    ProvenanceRecord,
    ResearchEvidenceRecord,
    RetrievalOutcome,
    ShareCountEvidence,
    SourceTier,
    assert_evidence_privacy,
    utc_now_iso,
)
from dsp_platform.research_retrieval.service import (
    ResearchRetrievalService,
    generate_stable_evidence_id,
)
from dsp_platform.research_retrieval.share_count_retriever import (
    RetrievalShareCountResolver,
    resolve_share_count_from_evidence,
)
from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    DnsResolutionError,
    DnsResolver,
    SafeHttpFetcher,
    SystemDnsResolver,
    UrlSafetyError,
    UrlSafetyPolicy,
    is_safe_ip_address,
    validate_url_safety,
)

__all__ = [
    "ConflictingClaim",
    "DeduplicationEngine",
    "DeduplicationResult",
    "DefaultSafeHttpFetcher",
    "DiscoveredSource",
    "DnsResolutionError",
    "DnsResolver",
    "DocumentValidationResult",
    "DocumentValidator",
    "EvidenceFreshness",
    "EvidenceStatus",
    "FetchedDocument",
    "GovernanceDecision",
    "ProvenanceRecord",
    "ResearchEvidenceRecord",
    "ResearchRetrievalService",
    "RetrievalGovernance",
    "RetrievalOutcome",
    "RetrievalShareCountResolver",
    "SafeHttpFetcher",
    "ShareCountEvidence",
    "SourceTier",
    "SystemDnsResolver",
    "UrlSafetyError",
    "UrlSafetyPolicy",
    "ValidationFailureReason",
    "assert_evidence_privacy",
    "canonicalize_url",
    "detect_prompt_injection",
    "generate_stable_evidence_id",
    "is_approved_host",
    "is_safe_ip_address",
    "normalize_source_name",
    "parse_indian_and_western_number",
    "resolve_share_count_from_evidence",
    "utc_now_iso",
    "validate_url_safety",
]
