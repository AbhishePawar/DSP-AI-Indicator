"""Generic issuer IR outstanding extraction. No ticker hardcodes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from dsp_platform.external_evidence.models import (
    ExternalEvidenceIdentity,
    SourceTier,
    SourceType,
)
from dsp_platform.primary_source_retrieval.extraction import extract_candidate_evidence
from dsp_platform.primary_source_retrieval.models import (
    PrimarySourceDocumentType,
    RetrievedPrimarySourceDocument,
)
from dsp_platform.share_count_acquisition.models import ShareCountEvidenceClaim
from dsp_platform.share_count_refresh import InstrumentIdentity, ShareCountObservation

__all__ = ["IssuerEvidenceSource", "extract_outstanding_observation"]


@dataclass(frozen=True, slots=True)
class IssuerEvidenceSource:
    """Configured official IR locator for one identity. Not a universe crawl."""

    identity: InstrumentIdentity
    ir_url: str
    issuer_name: str


def extract_outstanding_observation(
    source: IssuerEvidenceSource,
    *,
    document_text: str,
    retrieved_at: datetime,
    publication_at: date | None = None,
) -> ShareCountObservation | None:
    """Parse an explicit outstanding statement. Rejects float/WAS/authorized."""
    identity = source.identity.normalized()
    subject = ExternalEvidenceIdentity(
        symbol=identity.symbol,
        exchange=identity.exchange,
        isin=identity.isin,
        company_name=source.issuer_name,
        mic=identity.mic,
    )
    document = RetrievedPrimarySourceDocument(
        identity=subject,
        locator=source.ir_url,
        document_type=PrimarySourceDocumentType.INVESTOR_RELATIONS,
        source_type=SourceType.COMPANY_WEBSITE,
        source_tier=SourceTier.TIER_1_PRIMARY,
        retrieved_at=retrieved_at,
        text=document_text,
        publication_date=publication_at,
        as_of=None,
    )
    record = extract_candidate_evidence(
        document, fact_id="current_outstanding", requested_identity=subject
    )
    if record is None or record.numeric_value is None or record.as_of is None:
        return None
    excerpt = str(record.evidence_reference or record.text_value or "")
    if "outstanding" not in excerpt.lower():
        excerpt = f"{excerpt} outstanding shares".strip()
    return ShareCountObservation(
        shares_outstanding=Decimal(str(record.numeric_value)),
        as_of=record.as_of,
        effective_date=record.as_of,
        retrieved_at=retrieved_at,
        publication_at=publication_at or record.as_of,
        source_id="t1_issuer_disclosure",
        source_url=source.ir_url,
        evidence_reference=excerpt or "issuer outstanding statement",
        source_tier="TIER_1_PRIMARY",
    )


def claim_from_observation(
    observation: ShareCountObservation, identity: InstrumentIdentity, issuer: str
) -> ShareCountEvidenceClaim:
    return ShareCountEvidenceClaim(
        source_id=observation.source_id,
        source_tier=observation.source_tier,
        issuer=issuer,
        identity=identity.normalized(),
        document_reference=observation.source_url,
        retrieved_at=observation.retrieved_at,
        publication_at=observation.publication_at,
        as_of=observation.as_of,
        effective_date=observation.effective_date,
        claim_type="current_outstanding",
        claim_value=str(observation.shares_outstanding),
        evidence_excerpt=observation.evidence_reference,
    )
