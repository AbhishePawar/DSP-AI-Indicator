"""Canonical contracts for official-source research evidence (SIMPLE-14L).

LLMs are research agents, not authorities. Primary sources remain the
authority. Identity is ISIN + MIC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import uuid4

__all__ = [
    "AGENT_ROLES",
    "CAPITAL_EVENT_TYPES",
    "EVIDENCE_STAGES",
    "FAILURE_STATUSES",
    "PRICE_KINDS",
    "RESEARCH_MODES",
    "CheckStatus",
    "EvidenceItem",
    "EvidenceStage",
    "FailureStatus",
    "PriceKind",
    "PriceSnapshot",
    "ResearchAgentRole",
    "ResearchClaim",
    "ResearchMode",
    "ResearchRequest",
    "ResearchResult",
    "UdiffCashRow",
    "utc_now",
]

PriceKind = Literal[
    "REALTIME",
    "DELAYED_15M",
    "EOD",
    "PREVIOUS_CLOSE",
    "HISTORICAL",
    "UNKNOWN",
]
PRICE_KINDS: frozenset[str] = frozenset(
    {
        "REALTIME",
        "DELAYED_15M",
        "EOD",
        "PREVIOUS_CLOSE",
        "HISTORICAL",
        "UNKNOWN",
    }
)

EvidenceStage = Literal["RAW", "RECONCILED", "VERIFIED"]
EVIDENCE_STAGES: frozenset[str] = frozenset({"RAW", "RECONCILED", "VERIFIED"})

FailureStatus = Literal[
    "VERIFIED",
    "REFRESH_REQUIRED",
    "CONFLICT",
    "UNKNOWN",
    "UNAVAILABLE",
]
FAILURE_STATUSES: frozenset[str] = frozenset(
    {
        "VERIFIED",
        "REFRESH_REQUIRED",
        "CONFLICT",
        "UNKNOWN",
        "UNAVAILABLE",
    }
)

ResearchAgentRole = Literal[
    "gemini_find",
    "chatgpt_verify",
    "deep_search_attack",
    "claude_review",
    "dsp_judge",
    "official_nse_eod",
    "official_bse_eod",
]
AGENT_ROLES: frozenset[str] = frozenset(
    {
        "gemini_find",
        "chatgpt_verify",
        "deep_search_attack",
        "claude_review",
        "dsp_judge",
        "official_nse_eod",
        "official_bse_eod",
    }
)

ResearchMode = Literal["LIVE", "MOCK"]
RESEARCH_MODES: frozenset[str] = frozenset({"LIVE", "MOCK"})

CheckStatus = Literal["PASS", "FAIL", "UNKNOWN", "UNAVAILABLE"]

CAPITAL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "bonus",
        "split",
        "buyback",
        "rights",
        "qip",
        "fpo",
        "preferential_issue",
        "esop",
        "warrants",
        "convertibles",
        "cancellation",
        "capital_reduction",
        "merger",
        "demerger",
        "scheme",
        "share_swap",
    }
)


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _new_id() -> str:
    return str(uuid4())


@dataclass(frozen=True, slots=True)
class UdiffCashRow:
    """One UDiFF CM bhavcopy row with official field names preserved."""

    isin: str
    tckr_symb: str
    scty_srs: str
    trad_dt: date
    biz_dt: date
    cls_pric: Decimal | None
    last_pric: Decimal | None
    prvs_clsg_pric: Decimal | None
    sttlm_pric: Decimal | None
    src: str
    fin_instrm_tp: str
    fin_instrm_nm: str
    venue: Literal["NSE", "BSE"]
    raw: dict[str, str]

    def raw_field(self, name: str) -> str | None:
        value = self.raw.get(name)
        if value is None or not str(value).strip():
            return None
        return str(value).strip()


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """Canonical labeled price. Never silently rewrite previous close as current."""

    price: Decimal
    price_kind: PriceKind
    as_of: date
    retrieved_at: datetime
    currency: str
    source: str
    isin: str
    mic: str
    raw_price_field: str
    ticker: str | None = None
    venue: str | None = None
    source_url: str | None = None
    evidence_locator: str | None = None
    mode: ResearchMode = "LIVE"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "price": str(self.price),
            "price_kind": self.price_kind,
            "as_of": self.as_of.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "currency": self.currency,
            "source": self.source,
            "isin": self.isin,
            "mic": self.mic,
            "raw_price_field": self.raw_price_field,
            "ticker": self.ticker,
            "venue": self.venue,
            "source_url": self.source_url,
            "evidence_locator": self.evidence_locator,
            "mode": self.mode,
        }


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    """Immutable evidence ledger row. Agents cannot mutate status."""

    evidence_id: str
    company: str
    ticker: str
    isin: str
    mic: str
    field: str
    value: str | None
    as_of: date | None
    retrieved_at: datetime
    source: str
    source_type: str
    source_url: str | None
    document_date: date | None
    evidence_locator: str | None
    currency: str | None
    unit: str | None
    statement_basis: str | None
    agent: str
    identity_status: CheckStatus
    semantic_status: CheckStatus
    freshness_status: CheckStatus
    corporate_action_status: CheckStatus | FailureStatus
    confidence: str | None
    stage: EvidenceStage
    status: FailureStatus
    mode: ResearchMode
    raw_price_field: str | None = None
    current_through: date | None = None
    last_verified_at: datetime | None = None
    period: str | None = None
    raw_value: str | None = None
    raw_unit: str | None = None
    restated: bool = False

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "company": self.company,
            "ticker": self.ticker,
            "isin": self.isin,
            "mic": self.mic,
            "field": self.field,
            "value": self.value,
            "as_of": None if self.as_of is None else self.as_of.isoformat(),
            "retrieved_at": self.retrieved_at.isoformat(),
            "source": self.source,
            "source_type": self.source_type,
            "source_url": self.source_url,
            "document_date": (
                None if self.document_date is None else self.document_date.isoformat()
            ),
            "evidence_locator": self.evidence_locator,
            "currency": self.currency,
            "unit": self.unit,
            "statement_basis": self.statement_basis,
            "agent": self.agent,
            "identity_status": self.identity_status,
            "semantic_status": self.semantic_status,
            "freshness_status": self.freshness_status,
            "corporate_action_status": self.corporate_action_status,
            "confidence": self.confidence,
            "stage": self.stage,
            "status": self.status,
            "mode": self.mode,
            "raw_price_field": self.raw_price_field,
            "current_through": (
                None
                if self.current_through is None
                else self.current_through.isoformat()
            ),
            "last_verified_at": (
                None
                if self.last_verified_at is None
                else self.last_verified_at.isoformat()
            ),
            "period": self.period,
            "raw_value": self.raw_value,
            "raw_unit": self.raw_unit,
            "restated": self.restated,
        }


def new_evidence_id() -> str:
    return _new_id()


@dataclass(frozen=True, slots=True)
class ResearchRequest:
    """Provider-neutral research request. Identity must resolve to ISIN + MIC."""

    fields: tuple[str, ...]
    ticker: str | None = None
    company: str | None = None
    isin: str | None = None
    mic: str | None = None
    exchange: str | None = None
    as_of: date | None = None
    require_current: bool = False
    mode: ResearchMode = "LIVE"
    document_url: str | None = None
    candidate_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResearchClaim:
    """A proposed interpretation. Never automatically VERIFIED."""

    field: str
    value: str | None
    source_url: str | None
    document_locator: str | None
    agent: str
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class ResearchResult:
    identity_status: FailureStatus
    isin: str | None
    mic: str | None
    company: str | None
    ticker: str | None
    evidence: tuple[EvidenceItem, ...]
    price: PriceSnapshot | None
    claims: tuple[ResearchClaim, ...]
    unresolved: tuple[str, ...]
    mode: ResearchMode
    agent_outcomes: dict[str, FailureStatus] = field(default_factory=dict)

    def evidence_for(self, field: str) -> tuple[EvidenceItem, ...]:
        return tuple(item for item in self.evidence if item.field == field)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "identity_status": self.identity_status,
            "isin": self.isin,
            "mic": self.mic,
            "company": self.company,
            "ticker": self.ticker,
            "evidence": [item.to_public_dict() for item in self.evidence],
            "price": None if self.price is None else self.price.to_public_dict(),
            "claims": [
                {
                    "field": claim.field,
                    "value": claim.value,
                    "source_url": claim.source_url,
                    "document_locator": claim.document_locator,
                    "agent": claim.agent,
                    "notes": claim.notes,
                }
                for claim in self.claims
            ],
            "unresolved": list(self.unresolved),
            "mode": self.mode,
            "agent_outcomes": dict(self.agent_outcomes),
        }
