"""Architecture, dependency, and boundary enforcement tests for research retrieval."""

from __future__ import annotations

import inspect
import sys

from dsp_platform import research_retrieval


class TestResearchRetrievalArchitecture:
    def test_public_api_exports(self) -> None:
        expected = {
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
        }
        actual = set(research_retrieval.__all__)
        missing = expected - actual
        assert not missing, f"Missing exports in research_retrieval: {missing}"

    def test_no_forbidden_direct_network_imports_in_models(self) -> None:
        import dsp_platform.research_retrieval.models as models

        source = inspect.getsource(models)
        assert "socket" not in source
        assert "urllib.request" not in source
        assert "requests" not in source
        assert "httpx" not in source

    def test_no_valuation_or_recommendation_overrides_in_retrieval(self) -> None:
        """Ensure research retrieval does not import or alter DSP valuation or recommendation engines."""
        modules = [
            "dsp_platform.research_retrieval.models",
            "dsp_platform.research_retrieval.url_safety",
            "dsp_platform.research_retrieval.governance",
            "dsp_platform.research_retrieval.document_validator",
            "dsp_platform.research_retrieval.deduplication",
            "dsp_platform.research_retrieval.share_count_retriever",
            "dsp_platform.research_retrieval.service",
        ]
        for mod_name in modules:
            mod = sys.modules[mod_name]
            mod_source = inspect.getsource(mod)
            assert (
                "valuation" not in mod_source.lower() or "dcf" not in mod_source.lower()
            )
            assert (
                "recommendation" not in mod_source.lower()
                or "action" not in mod_source.lower()
            )
