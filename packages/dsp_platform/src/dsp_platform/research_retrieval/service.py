"""Central research retrieval service orchestrating safe discovery and validation."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from data_engine.share_count import ShareCount
from dsp_platform.research_retrieval.deduplication import (
    DeduplicationEngine,
    canonicalize_url,
)
from dsp_platform.research_retrieval.document_validator import DocumentValidator
from dsp_platform.research_retrieval.governance import (
    RetrievalGovernance,
    normalize_source_name,
)
from dsp_platform.research_retrieval.models import (
    DiscoveredSource,
    EvidenceFreshness,
    EvidenceStatus,
    FetchedDocument,
    ProvenanceRecord,
    ResearchEvidenceRecord,
    RetrievalOutcome,
    SourceTier,
    assert_evidence_privacy,
    utc_now_iso,
)
from dsp_platform.research_retrieval.share_count_retriever import (
    RetrievalShareCountResolver,
)
from dsp_platform.research_retrieval.url_safety import (
    DefaultSafeHttpFetcher,
    SafeHttpFetcher,
    UrlSafetyError,
    validate_url_safety,
)

__all__ = [
    "ResearchRetrievalService",
    "generate_stable_evidence_id",
]


def generate_stable_evidence_id(ticker: str, source: str, canonical_url: str, claim: str) -> str:
    """Generate a deterministic, stable evidence ID based on core provenance."""
    raw = f"{ticker.strip().upper()}|{source.strip().upper()}|{canonical_url.strip()}|{claim.strip()}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return f"ev_{digest}"


class ResearchRetrievalService:
    """Unified service for secure research discovery, retrieval, and validation."""

    def __init__(
        self,
        fetcher: SafeHttpFetcher | None = None,
        document_validator: DocumentValidator | None = None,
        governance: RetrievalGovernance | None = None,
        deduplicator: DeduplicationEngine | None = None,
        share_resolver: RetrievalShareCountResolver | None = None,
        clock: Callable[[], str] = utc_now_iso,
    ) -> None:
        self.fetcher = fetcher or DefaultSafeHttpFetcher()
        self.validator = document_validator or DocumentValidator()
        self.governance = governance or RetrievalGovernance()
        self.deduplicator = deduplicator or DeduplicationEngine()
        self.share_resolver = share_resolver or RetrievalShareCountResolver()
        self.clock = clock

    def process_discovered_sources(
        self,
        ticker: str,
        sources: Iterable[DiscoveredSource],
        share_candidates: Iterable[ShareCount] = (),
    ) -> RetrievalOutcome:
        """Run the full safe retrieval, document validation, and governance pipeline."""
        symbol = ticker.strip().upper()
        now_str = self.clock()

        evidence_records: list[ResearchEvidenceRecord] = []
        warnings: list[str] = []
        limitations: list[str] = []

        for candidate in sources:
            canon_url = canonicalize_url(candidate.url)
            norm_source = normalize_source_name(candidate.publisher or candidate.discovered_by)

            # 1. URL Safety Check
            try:
                validate_url_safety(candidate.url)
            except UrlSafetyError as err:
                evidence_records.append(
                    ResearchEvidenceRecord(
                        evidence_id=generate_stable_evidence_id(symbol, norm_source, canon_url, candidate.title),
                        ticker=symbol,
                        claim=candidate.title or "Discovered source",
                        status=EvidenceStatus.REJECTED,
                        provenance=ProvenanceRecord(
                            source=norm_source,
                            source_tier=candidate.source_tier,
                            provider=candidate.discovered_by,
                            publisher=candidate.publisher,
                            retrieved_at=now_str,
                            canonical_url=canon_url,
                            original_url=candidate.url,
                        ),
                        rejection_reason=f"URL safety validation failed: {err}",
                    )
                )
                warnings.append(f"Blocked unsafe source destination: {candidate.url} ({err})")
                continue

            # 2. Central Governance Policy Check
            gov_decision = self.governance.evaluate_source(
                source=norm_source,
                url=candidate.url,
                purpose="fundamental",
                publisher=candidate.publisher,
            )

            if not gov_decision.is_approved:
                evidence_records.append(
                    ResearchEvidenceRecord(
                        evidence_id=generate_stable_evidence_id(symbol, norm_source, canon_url, candidate.title),
                        ticker=symbol,
                        claim=candidate.title or "Discovered source",
                        status=EvidenceStatus.REJECTED,
                        provenance=ProvenanceRecord(
                            source=norm_source,
                            source_tier=gov_decision.source_tier,
                            provider=candidate.discovered_by,
                            publisher=candidate.publisher,
                            retrieved_at=now_str,
                            canonical_url=canon_url,
                            original_url=candidate.url,
                        ),
                        rejection_reason=gov_decision.rejection_reason or "Source not approved",
                    )
                )
                continue

            # 3. Secure Document Retrieval
            try:
                fetched_doc = self.fetcher.fetch(candidate.url)
            except Exception as exc:
                evidence_records.append(
                    ResearchEvidenceRecord(
                        evidence_id=generate_stable_evidence_id(symbol, norm_source, canon_url, candidate.title),
                        ticker=symbol,
                        claim=candidate.title or "Discovered source",
                        status=EvidenceStatus.UNAVAILABLE,
                        provenance=ProvenanceRecord(
                            source=norm_source,
                            source_tier=gov_decision.source_tier,
                            provider=candidate.discovered_by,
                            publisher=candidate.publisher,
                            retrieved_at=now_str,
                            canonical_url=canon_url,
                            original_url=candidate.url,
                        ),
                        rejection_reason=f"Retrieval error: {exc}",
                    )
                )
                limitations.append(f"Failed to retrieve source '{candidate.url}': {exc}")
                continue

            # 4. Document Content Validation
            val_result = self.validator.validate_claim(
                document=fetched_doc,
                ticker=symbol,
                claim=candidate.title or candidate.metadata.get("claim", ""),
                metric_name=candidate.metadata.get("metric_name"),
                claimed_value=float(candidate.metadata["metric_value"]) if "metric_value" in candidate.metadata else None,
                units=candidate.metadata.get("units"),
                claimed_period=candidate.metadata.get("period"),
            )

            rec_status = EvidenceStatus.VERIFIED if val_result.is_valid else EvidenceStatus.REJECTED
            evidence_records.append(
                ResearchEvidenceRecord(
                    evidence_id=generate_stable_evidence_id(symbol, norm_source, canon_url, candidate.title),
                    ticker=symbol,
                    claim=candidate.title or "Discovered source",
                    status=rec_status,
                    provenance=ProvenanceRecord(
                        source=norm_source,
                        source_tier=gov_decision.source_tier,
                        provider=candidate.discovered_by,
                        publisher=candidate.publisher,
                        retrieved_at=now_str,
                        published_at=candidate.metadata.get("published_at"),
                        effective_period=candidate.metadata.get("period"),
                        canonical_url=canon_url,
                        original_url=candidate.url,
                        content_hash=fetched_doc.content_hash,
                    ),
                    freshness=val_result.freshness,
                    metric_name=candidate.metadata.get("metric_name"),
                    metric_value=float(candidate.metadata["metric_value"]) if "metric_value" in candidate.metadata else None,
                    units=candidate.metadata.get("units"),
                    raw_excerpt=val_result.grounded_excerpt,
                    document_location=val_result.document_location,
                    rejection_reason=None if val_result.is_valid else str(val_result.failure_reason.value),
                )
            )

        # 5. Deduplication and Conflicting-Claim Reporting
        dedup_res = self.deduplicator.process_evidence(evidence_records)

        # 6. Authoritative Share-Count Resolution
        share_evidence = self.share_resolver.resolve(symbol, share_candidates)

        # 7. Categorization
        verified_items = tuple(r for r in dedup_res.unique_evidence if r.status is EvidenceStatus.VERIFIED)
        rejected_items = tuple(r for r in dedup_res.unique_evidence if r.status is EvidenceStatus.REJECTED)
        unverified_items = tuple(r for r in dedup_res.unique_evidence if r.status is EvidenceStatus.UNVERIFIED)
        stale_items = tuple(r for r in dedup_res.unique_evidence if r.freshness is EvidenceFreshness.STALE)

        overall_status = "success" if verified_items else ("empty" if not dedup_res.unique_evidence else "partial")

        outcome = RetrievalOutcome(
            status=overall_status,
            ticker=symbol,
            evidence_items=verified_items,
            conflicts=dedup_res.conflicts,
            share_count=share_evidence,
            stale_items=stale_items,
            unverified_items=unverified_items,
            rejected_items=rejected_items,
            warnings=tuple(warnings),
            coverage_limitations=tuple(limitations),
            retrieved_at=now_str,
        )

        # 8. Strict Privacy Audit (Ensure no prompts, secrets, or internal keys exist)
        assert_evidence_privacy(outcome)

        return outcome
