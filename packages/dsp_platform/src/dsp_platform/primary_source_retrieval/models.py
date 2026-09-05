"""Provider-neutral primary-source document retrieval models.

Retrieved documents are not evidence, not share-count authority, and not
valuation inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Any

from dsp_platform.external_evidence.models import (
    ExternalEvidenceIdentity,
    SourceTier,
    SourceType,
)

__all__ = [
    "DOCUMENT_RETRIEVAL_HANDLING",
    "DOCUMENT_RETRIEVAL_NOT_CONFIGURED",
    "DOCUMENT_RETRIEVAL_SCHEMA_VERSION",
    "PrimarySourceDocumentRequest",
    "PrimarySourceDocumentType",
    "RetrievedPrimarySourceDocument",
]

DOCUMENT_RETRIEVAL_SCHEMA_VERSION = "dsp.primary_source_document_retrieval.v1"
DOCUMENT_RETRIEVAL_NOT_CONFIGURED = "document_retrieval_not_configured"
DOCUMENT_RETRIEVAL_HANDLING = (
    "retrieved_document_not_validation_not_canonical_acceptance"
)


class PrimarySourceDocumentType(StrEnum):
    ANNUAL_REPORT = "annual_report"
    AUDITED_FINANCIAL_STATEMENTS = "audited_financial_statements"
    EXCHANGE_FILING = "exchange_filing"
    REGULATORY_FILING = "regulatory_filing"
    COMPANY_DISCLOSURE = "company_disclosure"
    INVESTOR_RELATIONS = "investor_relations"


@dataclass(frozen=True, slots=True)
class PrimarySourceDocumentRequest:
    """Explicit document locator request. Company name is never sufficient."""

    identity: ExternalEvidenceIdentity
    locator: str
    document_type: PrimarySourceDocumentType
    fact_id: str
    retrieved_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DOCUMENT_RETRIEVAL_SCHEMA_VERSION,
            "identity": self.identity.to_dict(),
            "locator": self.locator,
            "document_type": self.document_type.value,
            "fact_id": self.fact_id,
            "retrieved_at": self.retrieved_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class RetrievedPrimarySourceDocument:
    """Retrieved document envelope. Full text is for extraction only."""

    identity: ExternalEvidenceIdentity
    locator: str
    document_type: PrimarySourceDocumentType
    source_type: SourceType
    source_tier: SourceTier
    retrieved_at: datetime
    text: str
    media_type: str = "text/plain"
    publication_date: date | None = None
    as_of: date | None = None
    handling: str = DOCUMENT_RETRIEVAL_HANDLING
    requested_locator: str = ""
    final_locator: str = ""
    hostname: str = ""
    source_name: str = ""
    retrieval_status: str = "retrieved"

    def to_dict(self) -> dict[str, Any]:
        """Public metadata only — never dumps document text or secrets."""
        requested = self.requested_locator or self.locator
        final = self.final_locator or self.locator
        return {
            "schema_version": DOCUMENT_RETRIEVAL_SCHEMA_VERSION,
            "handling": self.handling,
            "canonical": False,
            "may_influence_calculation": False,
            "identity": self.identity.to_dict(),
            "locator": self.locator,
            "requested_locator": requested,
            "final_locator": final,
            "hostname": self.hostname,
            "source_name": self.source_name,
            "retrieval_status": self.retrieval_status,
            "document_type": self.document_type.value,
            "source_type": self.source_type.value,
            "source_tier": self.source_tier.value,
            "media_type": self.media_type,
            "retrieved_at": self.retrieved_at.isoformat(),
            "publication_date": (
                self.publication_date.isoformat()
                if self.publication_date is not None
                else None
            ),
            "as_of": self.as_of.isoformat() if self.as_of is not None else None,
            "text_length": len(self.text),
        }
