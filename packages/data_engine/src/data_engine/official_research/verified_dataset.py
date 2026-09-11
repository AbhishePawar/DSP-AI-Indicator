"""Canonical verified dataset — the only object allowed into deterministic DSP.

Missing evidence is UNKNOWN / UNAVAILABLE / REFRESH_REQUIRED / CONFLICT.
Fields are never invented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from data_engine.official_research.currentness import CapitalEvent
from data_engine.official_research.models import (
    EvidenceItem,
    FailureStatus,
    PriceSnapshot,
    ResearchMode,
)
from data_engine.official_research.semantics import ValuationGateResult

__all__ = [
    "AssumptionRecord",
    "DSPAnalysisResult",
    "FinancialField",
    "FinancialSnapshotVerified",
    "SecurityIdentity",
    "ShareCountSnapshot",
    "VerifiedDataset",
]


@dataclass(frozen=True, slots=True)
class SecurityIdentity:
    isin: str
    mic: str
    ticker: str
    company_name: str
    currency: str = "INR"


@dataclass(frozen=True, slots=True)
class ShareCountSnapshot:
    shares: Decimal
    as_of: date
    current_through: date
    last_verified_at: datetime
    source: str
    corporate_action_status: FailureStatus
    status: FailureStatus
    evidence_id: str | None = None
    source_url: str | None = None
    document_hash: str | None = None
    corporate_actions_checked: tuple[str, ...] = ()
    semantic_type: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialField:
    name: str
    value: Decimal | None
    status: FailureStatus
    as_of: date | None = None
    evidence_id: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialSnapshotVerified:
    revenue: FinancialField
    operating_profit: FinancialField
    ebit: FinancialField
    net_income: FinancialField
    equity: FinancialField
    cash: FinancialField
    cfo: FinancialField
    capex: FinancialField
    debt: FinancialField
    total_assets: FinancialField
    total_liabilities: FinancialField
    period_end: date | None
    statement_basis: str | None
    unit_scale: str | None


@dataclass(frozen=True, slots=True)
class AssumptionRecord:
    name: str
    source: str
    agent: str
    value: str | None
    unit: str | None
    period: str | None
    status: FailureStatus


@dataclass(frozen=True, slots=True)
class VerifiedDataset:
    """Provider-neutral DSP input. Non-VERIFIED fields must not be calculated on."""

    identity: SecurityIdentity | None
    identity_status: FailureStatus
    price: PriceSnapshot | None
    price_status: FailureStatus
    shares: ShareCountSnapshot | None
    shares_status: FailureStatus
    financials: FinancialSnapshotVerified | None
    corporate_action_status: FailureStatus
    evidence: tuple[EvidenceItem, ...]
    currentness_status: FailureStatus
    data_quality_status: FailureStatus
    valuation_gate: ValuationGateResult
    assumptions: tuple[AssumptionRecord, ...] = ()
    unresolved: tuple[str, ...] = ()
    mode: ResearchMode = "LIVE"
    capital_events: tuple[CapitalEvent, ...] = ()

    def field_status(self, name: str) -> FailureStatus:
        if name == "price":
            return self.price_status
        if name == "shares":
            return self.shares_status
        if self.financials is None:
            return "UNAVAILABLE"
        item = getattr(self.financials, name, None)
        if isinstance(item, FinancialField):
            return item.status
        return "UNAVAILABLE"

    def verified_decimal(self, name: str) -> Decimal | None:
        status = self.field_status(name)
        if status != "VERIFIED":
            return None
        if name == "price" and self.price is not None:
            return self.price.price
        if name == "shares" and self.shares is not None:
            return self.shares.shares
        if self.financials is None:
            return None
        item = getattr(self.financials, name, None)
        if isinstance(item, FinancialField):
            return item.value
        return None

    def to_public_dict(self) -> dict[str, Any]:
        identity = None
        if self.identity is not None:
            identity = {
                "isin": self.identity.isin,
                "mic": self.identity.mic,
                "ticker": self.identity.ticker,
                "company_name": self.identity.company_name,
                "currency": self.identity.currency,
            }
        price = None if self.price is None else self.price.to_public_dict()
        shares = None
        if self.shares is not None:
            shares = {
                "shares_outstanding": str(self.shares.shares),
                "shares_as_of": self.shares.as_of.isoformat(),
                "shares_current_through": self.shares.current_through.isoformat(),
                "shares_last_verified_at": self.shares.last_verified_at.isoformat(),
                "source": self.shares.source,
                "source_url": self.shares.source_url,
                "document_hash": self.shares.document_hash,
                "corporate_action_status": self.shares.corporate_action_status,
                "corporate_actions_checked": list(self.shares.corporate_actions_checked),
                "semantic_type": self.shares.semantic_type,
                "status": self.shares.status,
            }
        financials = None
        if self.financials is not None:
            financials = {
                field.name: {
                    "value": None if field.value is None else str(field.value),
                    "status": field.status,
                    "as_of": None if field.as_of is None else field.as_of.isoformat(),
                    "source": field.source,
                }
                for field in (
                    self.financials.revenue,
                    self.financials.operating_profit,
                    self.financials.ebit,
                    self.financials.net_income,
                    self.financials.equity,
                    self.financials.cash,
                    self.financials.cfo,
                    self.financials.capex,
                    self.financials.debt,
                    self.financials.total_assets,
                    self.financials.total_liabilities,
                )
            }
            financials["period_end"] = (
                None
                if self.financials.period_end is None
                else self.financials.period_end.isoformat()
            )
            financials["statement_basis"] = self.financials.statement_basis
            financials["unit_scale"] = self.financials.unit_scale
        return {
            "identity": identity,
            "identity_status": self.identity_status,
            "price": price,
            "price_status": self.price_status,
            "shares": shares,
            "shares_status": self.shares_status,
            "financials": financials,
            "corporate_action_status": self.corporate_action_status,
            "currentness_status": self.currentness_status,
            "data_quality_status": self.data_quality_status,
            "valuation_gate": {
                "method": self.valuation_gate.method,
                "status": self.valuation_gate.status,
                "detail": self.valuation_gate.detail,
            },
            "assumptions": [
                {
                    "name": item.name,
                    "source": item.source,
                    "agent": item.agent,
                    "value": item.value,
                    "unit": item.unit,
                    "period": item.period,
                    "status": item.status,
                }
                for item in self.assumptions
            ],
            "unresolved": list(self.unresolved),
            "mode": self.mode,
            "evidence": [item.to_public_dict() for item in self.evidence],
        }


@dataclass(frozen=True, slots=True)
class DSPAnalysisResult:
    identity: dict[str, Any] | None
    data_status: FailureStatus
    overall_score: float | None
    quality: FailureStatus
    business_quality: FailureStatus
    management_quality: FailureStatus
    moat: FailureStatus
    risk: FailureStatus
    financial_quality: FailureStatus
    valuation: FailureStatus
    buffett_indicator: FailureStatus
    margin_of_safety: FailureStatus
    evidence: tuple[EvidenceItem, ...]
    confidence: str | None
    currentness: FailureStatus
    unresolved_issues: tuple[str, ...]
    allowed_methods: tuple[str, ...] = ()
    dataset: VerifiedDataset | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "identity": self.identity,
            "data_status": self.data_status,
            "overall_score": self.overall_score,
            "quality": self.quality,
            "business_quality": self.business_quality,
            "management_quality": self.management_quality,
            "moat": self.moat,
            "risk": self.risk,
            "financial_quality": self.financial_quality,
            "valuation": self.valuation,
            "buffett_indicator": self.buffett_indicator,
            "margin_of_safety": self.margin_of_safety,
            "confidence": self.confidence,
            "currentness": self.currentness,
            "unresolved_issues": list(self.unresolved_issues),
            "allowed_methods": list(self.allowed_methods),
            "evidence": [item.to_public_dict() for item in self.evidence],
        }
