"""Evidence-based research retrieval layer models and privacy contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

__all__ = [
    "EvidenceFreshness",
    "EvidenceStatus",
    "SourceTier",
    "DiscoveredSource",
    "FetchedDocument",
    "ProvenanceRecord",
    "ResearchEvidenceRecord",
    "ShareCountEvidence",
    "ConflictingClaim",
    "RetrievalOutcome",
    "assert_evidence_privacy",
    "utc_now_iso",
]

# Sensitive terms that must never leak into evidence records or public payloads.
FORBIDDEN_LEAKAGE_TERMS = frozenset(
    {
        "api_key",
        "api_keys",
        "chain_of_thought",
        "cot",
        "model_name",
        "private_prompt",
        "raw_tool_payloads",
        "routing_reason",
        "secret",
        "secrets",
        "system_prompt",
    }
)


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO-8601 format."""
    return datetime.now(tz=UTC).isoformat()


class EvidenceStatus(StrEnum):
    """Lifecycle and verification status of a research evidence record."""

    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"
    STALE = "stale"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"


class SourceTier(StrEnum):
    """Authority classification of a source."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    MARKET_DATA = "market_data"
    UNAPPROVED = "unapproved"


class EvidenceFreshness(StrEnum):
    """Freshness assessment of retrieved evidence."""

    CURRENT = "current"
    HISTORICAL = "historical"
    STALE = "stale"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class DiscoveredSource:
    """A discovered candidate source prior to safe fetching and validation."""

    url: str
    publisher: str
    title: str = ""
    source_tier: SourceTier = SourceTier.UNAPPROVED
    discovered_by: str = "shared_retrieval"
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "publisher": self.publisher,
            "title": self.title,
            "source_tier": self.source_tier.value,
            "discovered_by": self.discovered_by,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    """A securely retrieved document representation."""

    url: str
    final_url: str
    status_code: int
    content_type: str
    text_content: str
    content_hash: str
    fetched_at: str
    redirect_chain: tuple[str, ...] = ()
    headers: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url,
            "status_code": self.status_code,
            "content_type": self.content_type,
            "content_hash": self.content_hash,
            "fetched_at": self.fetched_at,
            "redirect_count": len(self.redirect_chain),
        }


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    """Traceable provenance for a verified or unverified piece of evidence."""

    source: str
    source_tier: SourceTier
    provider: str
    retrieved_at: str
    canonical_url: str
    original_url: str
    publisher: str = ""
    published_at: str | None = None
    effective_period: str | None = None
    document_id: str | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_tier": self.source_tier.value,
            "provider": self.provider,
            "publisher": self.publisher,
            "retrieved_at": self.retrieved_at,
            "published_at": self.published_at,
            "effective_period": self.effective_period,
            "document_id": self.document_id,
            "canonical_url": self.canonical_url,
            "original_url": self.original_url,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True, slots=True)
class ResearchEvidenceRecord:
    """Normalized, governed research evidence item."""

    evidence_id: str
    ticker: str
    claim: str
    status: EvidenceStatus
    provenance: ProvenanceRecord
    freshness: EvidenceFreshness = EvidenceFreshness.UNKNOWN
    metric_name: str | None = None
    metric_value: float | None = None
    units: str | None = None
    raw_excerpt: str = ""
    document_location: str | None = None
    rejection_reason: str | None = None
    corroborated_by: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "ticker": self.ticker,
            "claim": self.claim,
            "status": self.status.value,
            "freshness": self.freshness.value,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "units": self.units,
            "provenance": self.provenance.to_dict(),
            "raw_excerpt": self.raw_excerpt,
            "document_location": self.document_location,
            "rejection_reason": self.rejection_reason,
            "corroborated_by": list(self.corroborated_by),
            "conflicts_with": list(self.conflicts_with),
        }


@dataclass(frozen=True, slots=True)
class ShareCountEvidence:
    """Share count evidence with primary authority and cross-check flags."""

    ticker: str
    shares: float
    as_of: str
    source: str
    is_primary: bool
    verified: bool
    cross_checked: bool = False
    discrepancy_flag: bool = False
    evidence_id: str | None = None
    secondary_sources: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "shares": self.shares,
            "as_of": self.as_of,
            "source": self.source,
            "is_primary": self.is_primary,
            "verified": self.verified,
            "cross_checked": self.cross_checked,
            "discrepancy_flag": self.discrepancy_flag,
            "evidence_id": self.evidence_id,
            "secondary_sources": list(self.secondary_sources),
        }


@dataclass(frozen=True, slots=True)
class ConflictingClaim:
    """Discrepancy report when sources contradict each other on a material fact."""

    ticker: str
    metric_name: str
    period: str | None
    primary_claim: ResearchEvidenceRecord
    conflicting_claim: ResearchEvidenceRecord
    discrepancy_pct: float | None
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "metric_name": self.metric_name,
            "period": self.period,
            "primary_evidence_id": self.primary_claim.evidence_id,
            "conflicting_evidence_id": self.conflicting_claim.evidence_id,
            "discrepancy_pct": self.discrepancy_pct,
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    """Aggregated output of the research retrieval layer."""

    status: str
    ticker: str
    evidence_items: tuple[ResearchEvidenceRecord, ...] = ()
    conflicts: tuple[ConflictingClaim, ...] = ()
    share_count: ShareCountEvidence | None = None
    stale_items: tuple[ResearchEvidenceRecord, ...] = ()
    unverified_items: tuple[ResearchEvidenceRecord, ...] = ()
    rejected_items: tuple[ResearchEvidenceRecord, ...] = ()
    warnings: tuple[str, ...] = ()
    coverage_limitations: tuple[str, ...] = ()
    retrieved_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "ticker": self.ticker,
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "share_count": self.share_count.to_dict() if self.share_count else None,
            "stale_items": [item.to_dict() for item in self.stale_items],
            "unverified_items": [item.to_dict() for item in self.unverified_items],
            "rejected_items": [item.to_dict() for item in self.rejected_items],
            "warnings": list(self.warnings),
            "coverage_limitations": list(self.coverage_limitations),
            "retrieved_at": self.retrieved_at,
        }


def assert_evidence_privacy(data: Any) -> None:
    """Ensure no private prompt, credential, or AI internal leaked into evidence payloads."""
    if isinstance(data, dict):
        for k, v in data.items():
            key_str = str(k).lower()
            for forbidden in FORBIDDEN_LEAKAGE_TERMS:
                if forbidden in key_str:
                    raise ValueError(
                        f"Privacy breach: forbidden key {k} in evidence payload"
                    )
            assert_evidence_privacy(v)
    elif isinstance(data, (list, tuple)):
        for item in data:
            assert_evidence_privacy(item)
    elif hasattr(data, "to_dict"):
        assert_evidence_privacy(data.to_dict())
