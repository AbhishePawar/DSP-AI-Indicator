"""Central research retrieval service orchestrating safe discovery and validation."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Iterable

from data_engine import ShareCount
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
    ProvenanceRecord,
    ResearchEvidenceRecord,
    RetrievalOutcome,
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


def generate_stable_evidence_id(
    ticker: str,
    source: str,
    canonical_url: str,
    claim: str,
    *,
    metric_name: str | None = None,
    metric_value: float | None = None,
    units: str | None = None,
    period: str | None = None,
) -> str:
    """Generate a deterministic, stable evidence ID based on core provenance.

    Metric identity (name, value, units, period) is part of the ID so two
    different facts published in the same document never collapse into one.
    Calls without metric fields keep their previous IDs.
    """
    raw_text = f"{ticker.strip().upper()}|{source.strip().upper()}|{canonical_url.strip()}|{claim.strip()}"
    if metric_name or metric_value is not None or units or period:
        raw_text += (
            f"|{(metric_name or '').strip().upper()}|{'' if metric_value is None else repr(float(metric_value))}"
            f"|{(units or '').strip().upper()}|{(period or '').strip().upper()}"
        )
    raw = raw_text.encode()
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
            claimed_value, value_error = _parse_metric_value(candidate.metadata.get("metric_value"))
            if value_error:
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
                            content_hash=fetched_doc.content_hash,
                        ),
                        rejection_reason=value_error,
                    )
                )
                limitations.append(f"Skipped source '{candidate.url}': {value_error}")
                continue

            val_result = self.validator.validate_claim(
                document=fetched_doc,
                ticker=symbol,
                claim=candidate.title or candidate.metadata.get("claim", ""),
                metric_name=candidate.metadata.get("metric_name"),
                claimed_value=claimed_value,
                units=candidate.metadata.get("units"),
                claimed_period=candidate.metadata.get("period"),
            )

            # Grounded content never upgrades the source: a source governance only allows
            # for cross-checking stays UNVERIFIED even when its text matches.
            if not val_result.is_valid:
                rec_status = EvidenceStatus.REJECTED
                rec_reason: str | None = str(val_result.failure_reason.value)
            elif gov_decision.status is EvidenceStatus.VERIFIED:
                rec_status = EvidenceStatus.VERIFIED
                rec_reason = None
            else:
                rec_status = EvidenceStatus.UNVERIFIED
                rec_reason = gov_decision.rejection_reason or "Source not approved as primary authority"
            evidence_records.append(
                ResearchEvidenceRecord(
                    evidence_id=generate_stable_evidence_id(
                        symbol,
                        norm_source,
                        canon_url,
                        candidate.title,
                        metric_name=candidate.metadata.get("metric_name"),
                        metric_value=claimed_value,
                        units=candidate.metadata.get("units"),
                        period=candidate.metadata.get("period"),
                    ),
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
                    metric_value=claimed_value,
                    units=candidate.metadata.get("units"),
                    raw_excerpt=val_result.grounded_excerpt,
                    document_location=val_result.document_location,
                    rejection_reason=rec_reason,
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


def _parse_metric_value(raw: object) -> tuple[float | None, str | None]:
    """Parse a source's claimed metric value; returns (value, error) so one bad source cannot abort the batch."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None, None
    try:
        value = float(str(raw).replace(",", "").strip())
    except ValueError:
        return None, f"Invalid metric_value {str(raw)[:40]!r}"
    if not math.isfinite(value):
        return None, f"Non-finite metric_value {str(raw)[:40]!r}"
    return value, None
