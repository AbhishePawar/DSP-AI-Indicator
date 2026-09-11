"""Canonical assumption contract. Assumptions are not verified facts.

AI may propose. DSP must validate. PROPOSED never enters final calculations.
Existing AssumptionRecord on VerifiedDataset is unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

__all__ = [
    "ASSUMPTION_FIELDS",
    "ASSUMPTION_SOURCES",
    "ASSUMPTION_STATUSES",
    "CIRCULAR_ASSUMPTION_SOURCES",
    "CanonicalAssumption",
    "DATA_CLASS_ASSUMPTION",
    "DATA_CLASS_DERIVED",
    "DATA_CLASS_FACT",
    "DERIVED_FIELDS",
    "FACT_FIELDS",
    "SCENARIOS",
    "assumption",
    "classify_data_class",
    "new_assumption_id",
]

DATA_CLASS_FACT = "VERIFIED_FACT"
DATA_CLASS_DERIVED = "DERIVED_VALUE"
DATA_CLASS_ASSUMPTION = "ASSUMPTION"

ASSUMPTION_STATUSES: frozenset[str] = frozenset(
    {
        "PROPOSED",
        "ACCEPTED",
        "REJECTED",
        "UNKNOWN",
        "USER_REQUIRED",
        "REVIEW_REQUIRED",
    }
)

SCENARIOS: frozenset[str] = frozenset({"BEAR", "BASE", "BULL"})

ASSUMPTION_SOURCES: frozenset[str] = frozenset(
    {
        "historical_company_performance",
        "management_guidance",
        "company_filings",
        "industry_data",
        "regulatory_information",
        "macro_data",
        "primary_research",
        "ai_synthesis",
    }
)

FACT_FIELDS: frozenset[str] = frozenset(
    {
        "revenue",
        "net_income",
        "cfo",
        "capex",
        "cash",
        "debt",
        "shares",
        "shares_outstanding",
        "price",
        "eod_close",
        "operating_profit",
        "ebit",
        "equity",
        "total_assets",
        "total_liabilities",
        "gdp",
        "total_market_cap",
    }
)

DERIVED_FIELDS: frozenset[str] = frozenset(
    {
        "fcf",
        "market_cap",
        "net_debt",
        "enterprise_value",
        "fcf_yield",
        "ev_ebit",
        "ev_ebitda",
        "price_to_earnings",
        "intrinsic_value",
        "intrinsic_value_per_share",
        "margin_of_safety",
        "equity_value",
        "dcf",
        "terminal_value",
    }
)

ASSUMPTION_FIELDS: frozenset[str] = frozenset(
    {
        "discount_rate",
        "wacc",
        "fcf_growth_rate",
        "revenue_growth",
        "terminal_growth_rate",
        "operating_margin",
        "tax_rate",
        "earnings_multiple",
        "owner_earnings_cap_rate",
        "residual_income_required_return",
        "projection_years",
        "beta",
        "risk_free_rate",
        "equity_risk_premium",
    }
)

CIRCULAR_ASSUMPTION_SOURCES: frozenset[str] = frozenset(
    {
        "intrinsic_value",
        "intrinsic_value_per_share",
        "margin_of_safety",
        "dcf",
        "ai_valuation",
        "market_cap",
        "enterprise_value",
        "equity_value",
        "fcf_yield",
    }
)

_AI_PROPOSERS: frozenset[str] = frozenset(
    {
        "ai",
        "ai_synthesis",
        "gemini_find",
        "chatgpt_verify",
        "deep_search_attack",
        "claude_review",
        "openai_nse_mcp",
        "openai",
    }
)


def new_assumption_id(field: str, scenario: str = "BASE") -> str:
    return f"asm-{scenario.lower()}-{field}"


def classify_data_class(field: str) -> str:
    name = str(field or "").strip().lower()
    if name in FACT_FIELDS:
        return DATA_CLASS_FACT
    if name in DERIVED_FIELDS:
        return DATA_CLASS_DERIVED
    if name in ASSUMPTION_FIELDS:
        return DATA_CLASS_ASSUMPTION
    return "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CanonicalAssumption:
    """Forward-looking input. Not a historical fact. Not derived output."""

    assumption_id: str
    field: str
    value: Decimal | None
    unit: str | None
    period: str | None
    scenario: str
    source: str
    evidence_ids: tuple[str, ...]
    reasoning: str
    proposed_by: str
    validated_by: str | None
    validation_status: str
    confidence: str | None
    created_at: datetime
    detail: str = ""

    def __post_init__(self) -> None:
        if self.validation_status not in ASSUMPTION_STATUSES:
            raise ValueError(f"invalid assumption status: {self.validation_status}")
        if self.scenario not in SCENARIOS:
            raise ValueError(f"invalid scenario: {self.scenario}")
        if classify_data_class(self.field) != DATA_CLASS_ASSUMPTION:
            raise ValueError(f"{self.field} is not an assumption field")

    @property
    def proposed_by_ai(self) -> bool:
        return self.proposed_by.strip().lower() in _AI_PROPOSERS

    @property
    def source_is_ai_synthesis(self) -> bool:
        return self.source.strip().lower() == "ai_synthesis"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "field": self.field,
            "value": None if self.value is None else str(self.value),
            "unit": self.unit,
            "period": self.period,
            "scenario": self.scenario,
            "source": self.source,
            "evidence_ids": list(self.evidence_ids),
            "reasoning": self.reasoning,
            "proposed_by": self.proposed_by,
            "validated_by": self.validated_by,
            "validation_status": self.validation_status,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "detail": self.detail,
            "data_class": DATA_CLASS_ASSUMPTION,
        }


def assumption(
    field: str,
    value: Decimal | str | float | int | None,
    *,
    scenario: str = "BASE",
    source: str = "primary_research",
    proposed_by: str = "analyst",
    validation_status: str = "PROPOSED",
    unit: str | None = "decimal",
    period: str | None = None,
    evidence_ids: tuple[str, ...] = (),
    reasoning: str = "",
    confidence: str | None = None,
    created_at: datetime | None = None,
    assumption_id: str | None = None,
    validated_by: str | None = None,
    detail: str = "",
) -> CanonicalAssumption:
    numeric: Decimal | None
    if value is None:
        numeric = None
    elif isinstance(value, Decimal):
        numeric = value
    else:
        numeric = Decimal(str(value))
    return CanonicalAssumption(
        assumption_id=assumption_id or new_assumption_id(field, scenario),
        field=field,
        value=numeric,
        unit=unit,
        period=period,
        scenario=scenario,
        source=source,
        evidence_ids=evidence_ids,
        reasoning=reasoning,
        proposed_by=proposed_by,
        validated_by=validated_by,
        validation_status=validation_status,
        confidence=confidence,
        created_at=created_at or datetime.now(tz=UTC),
        detail=detail,
    )
