"""SIMPLE-14H research contracts: request, claim, evidence.

Claims are candidates. Only the quality gate may emit VERIFIED_DATA.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from data_engine.data_states import DataState
from data_engine.security_identity import IdentityStatus, SecurityIdentity

__all__ = [
    "AUTHORITATIVE_FINANCIAL_FIELDS",
    "BUSINESS_RESEARCH_FIELDS",
    "CurrentnessStatus",
    "EvidenceRecord",
    "ResearchClaim",
    "ResearchRequest",
    "ShareCapitalKind",
]


class ShareCapitalKind(StrEnum):
    AUTHORIZED = "authorized"
    ISSUED = "issued"
    PAID_UP = "paid_up"
    LISTED = "listed"
    FREE_FLOAT = "free_float"
    PROMOTER = "promoter"
    OUTSTANDING = "outstanding"


class CurrentnessStatus(StrEnum):
    CURRENT = "CURRENT"
    REFRESH_REQUIRED = "REFRESH_REQUIRED"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


AUTHORITATIVE_FINANCIAL_FIELDS = frozenset(
    {
        "revenue",
        "ebitda",
        "ebit",
        "pat",
        "eps",
        "cfo",
        "fcf",
        "assets",
        "liabilities",
        "debt",
        "cash",
        "equity",
        "working_capital",
        "roe",
        "roce",
        "margins",
        "shares_outstanding",
        "current_price",
    }
)

BUSINESS_RESEARCH_FIELDS = frozenset(
    {
        "business_model",
        "products",
        "customers",
        "geography",
        "revenue_drivers",
        "switching_costs",
        "network_effects",
        "brand",
        "scale",
        "distribution",
        "cost_advantage",
        "regulatory_advantage",
        "ownership",
        "capital_allocation",
        "governance",
        "related_parties",
        "compensation",
        "insider_ownership",
        "leverage",
        "liquidity",
        "competition",
        "regulation",
        "concentration",
        "cyclicality",
        "disruption",
    }
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    research_request_id: str
    company: str
    ticker: str
    isin: str
    exchange: str
    mic: str
    requested_fields: tuple[str, ...]
    requested_as_of: str
    research_purpose: str
    created_at: datetime
    security_type: str = ""
    listing_status: str = ""
    identity_status: str = ""

    @classmethod
    def from_identity(
        cls,
        identity: SecurityIdentity,
        *,
        requested_fields: tuple[str, ...],
        requested_as_of: str,
        research_purpose: str,
        created_at: datetime,
        research_request_id: str | None = None,
    ) -> ResearchRequest:
        return cls(
            research_request_id=research_request_id or _new_id("rr"),
            company=identity.company,
            ticker=identity.ticker,
            isin=identity.isin,
            exchange=identity.exchange,
            mic=identity.mic,
            requested_fields=requested_fields,
            requested_as_of=requested_as_of,
            research_purpose=research_purpose,
            created_at=created_at,
            security_type=identity.security_type,
            listing_status=identity.listing_status,
            identity_status=(
                identity.status.value
                if isinstance(identity.status, IdentityStatus)
                else str(identity.status)
            ),
        )

    def identity_key(self) -> str:
        if self.isin and self.mic:
            return f"{self.isin}|{self.mic}"
        return f"{self.ticker}|{self.exchange}"


@dataclass(frozen=True, slots=True)
class ResearchClaim:
    claim_id: str
    research_request_id: str
    company: str
    ticker: str
    isin: str
    mic: str
    field: str
    candidate_value: str
    unit: str
    currency: str
    period: str
    as_of: str
    agent: str
    source: str
    source_type: str
    source_url: str
    document_date: str
    evidence_locator: str
    retrieved_at: datetime
    agent_confidence: float | None = None
    exchange: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "claim_id": self.claim_id,
            "research_request_id": self.research_request_id,
            "ticker": self.ticker,
            "isin": self.isin,
            "mic": self.mic,
            "field": self.field,
            "candidate_value": self.candidate_value,
            "source": self.source,
            "agent": self.agent,
            "source_url": self.source_url,
        }


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    claim_id: str
    company: str
    ticker: str
    isin: str
    mic: str
    field: str
    value: str
    unit: str
    currency: str
    period: str
    as_of: str
    retrieved_at: datetime
    source: str
    source_type: str
    source_url: str
    document_date: str
    evidence_locator: str
    agent: str
    identity_status: str
    semantic_status: str
    freshness_status: str
    corporate_action_status: str
    confidence: float | None
    data_state: DataState = DataState.RAW_PROVIDER_DATA
    injection_suspect: bool = False
    notes: tuple[str, ...] = dc_field(default_factory=tuple)

    @classmethod
    def from_claim(
        cls,
        claim: ResearchClaim,
        *,
        identity_status: str,
        semantic_status: str = "UNKNOWN",
        freshness_status: str = "UNKNOWN",
        corporate_action_status: str = "UNKNOWN",
        data_state: DataState = DataState.RAW_PROVIDER_DATA,
        injection_suspect: bool = False,
        notes: tuple[str, ...] = (),
    ) -> EvidenceRecord:
        return cls(
            evidence_id=_new_id("ev"),
            claim_id=claim.claim_id,
            company=claim.company,
            ticker=claim.ticker,
            isin=claim.isin,
            mic=claim.mic,
            field=claim.field,
            value=claim.candidate_value,
            unit=claim.unit,
            currency=claim.currency,
            period=claim.period,
            as_of=claim.as_of,
            retrieved_at=claim.retrieved_at,
            source=claim.source,
            source_type=claim.source_type,
            source_url=claim.source_url,
            document_date=claim.document_date,
            evidence_locator=claim.evidence_locator,
            agent=claim.agent,
            identity_status=identity_status,
            semantic_status=semantic_status,
            freshness_status=freshness_status,
            corporate_action_status=corporate_action_status,
            confidence=claim.agent_confidence,
            data_state=data_state,
            injection_suspect=injection_suspect,
            notes=notes,
        )
