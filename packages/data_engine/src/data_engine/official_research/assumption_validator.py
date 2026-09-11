"""Validate AI-proposed assumptions. AI confidence is not proof.

Bounds are copied from existing valuation engines, not invented per ticker:

* discount_rate / WACC > 0 (ValuationAssumptions)
* fcf_growth / revenue_growth in [-0.5, 0.5] (DcfForecastAssumptions)
* terminal_growth in [0, 0.08] and strictly < WACC (ValuationAssumptions + DcfTerminalAssumptions)
* operating_margin in [-0.5, 0.8] (DcfForecastAssumptions)
* tax_rate in [0, 1) (DcfForecastAssumptions)
* projection_years in [1, 30] (DcfForecastAssumptions max; ValuationAssumptions min 1)

Unusual but in-bound pairs may be REVIEW_REQUIRED. Out-of-bound values are REJECTED.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Mapping

from data_engine.official_research.assumption_contract import (
    ASSUMPTION_SOURCES,
    CIRCULAR_ASSUMPTION_SOURCES,
    CanonicalAssumption,
    DATA_CLASS_ASSUMPTION,
    DATA_CLASS_DERIVED,
    DATA_CLASS_FACT,
    DERIVED_FIELDS,
    FACT_FIELDS,
    SCENARIOS,
    classify_data_class,
)
from data_engine.official_research.extraction import (
    canonicalize_period,
    normalize_numeric_to_actual,
    periods_comparable,
)

__all__ = [
    "ASSUMPTION_BOUNDS",
    "AssumptionValidation",
    "ai_assumption_workflow",
    "classify_data_class",
    "refuse_ai_fact",
    "refuse_circular_assumption",
    "million_not_equal_crore",
    "units_compatible",
    "validate_assumption",
    "validate_assumption_pack",
]

# Inclusive bounds unless noted. Justified by existing valuation constructors.
ASSUMPTION_BOUNDS: dict[str, tuple[Decimal | None, Decimal | None, str]] = {
    "discount_rate": (Decimal("0.0000001"), Decimal("0.40"), "open_low"),
    "wacc": (Decimal("0.0000001"), Decimal("0.40"), "open_low"),
    "fcf_growth_rate": (Decimal("-0.5"), Decimal("0.5"), "closed"),
    "revenue_growth": (Decimal("-0.5"), Decimal("0.5"), "closed"),
    "terminal_growth_rate": (Decimal("0"), Decimal("0.08"), "closed"),
    "operating_margin": (Decimal("-0.5"), Decimal("0.8"), "closed"),
    "tax_rate": (Decimal("0"), Decimal("1"), "open_high"),
    "earnings_multiple": (Decimal("0.0000001"), Decimal("80"), "open_low"),
    "owner_earnings_cap_rate": (Decimal("0.0000001"), Decimal("0.40"), "open_low"),
    "residual_income_required_return": (Decimal("0.0000001"), Decimal("0.40"), "open_low"),
    "projection_years": (Decimal("1"), Decimal("30"), "closed"),
    "beta": (Decimal("0.0000001"), Decimal("5"), "open_low"),
    "risk_free_rate": (Decimal("-0.05"), Decimal("0.25"), "closed"),
    "equity_risk_premium": (Decimal("0.0000001"), Decimal("0.20"), "open_low"),
}

_RATE_UNITS = frozenset({"decimal", "ratio", "percent", "pct", "%"})
_YEAR_UNITS = frozenset({"years", "year", "integer", "count"})
_GROWTH_DIVERGENCE = Decimal("0.20")


@dataclass(frozen=True, slots=True)
class AssumptionValidation:
    assumption: CanonicalAssumption
    status: str
    detail: str
    data_class: str = DATA_CLASS_ASSUMPTION

    @property
    def accepted(self) -> bool:
        return self.status == "ACCEPTED"


def refuse_ai_fact(field: str, *, proposed_by: str, status: str | None = None) -> str | None:
    """AI may not establish a numeric financial fact."""
    if classify_data_class(field) != DATA_CLASS_FACT:
        return None
    agent = proposed_by.strip().lower()
    if agent in {
        "ai",
        "ai_synthesis",
        "gemini_find",
        "chatgpt_verify",
        "deep_search_attack",
        "claude_review",
        "openai_nse_mcp",
        "openai",
    }:
        return "REJECTED"
    if status and status != "VERIFIED":
        return "REJECTED"
    return None


def refuse_circular_assumption(field: str, *, source_fields: tuple[str, ...]) -> bool:
    if classify_data_class(field) != DATA_CLASS_ASSUMPTION:
        return True
    if field in DERIVED_FIELDS:
        return True
    return any(
        item in CIRCULAR_ASSUMPTION_SOURCES or item in DERIVED_FIELDS
        for item in source_fields
    )


def units_compatible(left: str | None, right: str | None) -> bool:
    a = str(left or "").strip().lower()
    b = str(right or "").strip().lower()
    if not a or not b:
        return False
    if a == b:
        return True
    decimal_like = {"decimal", "ratio"}
    percent_like = {"percent", "pct", "%"}
    if a in decimal_like and b in decimal_like:
        return True
    if a in percent_like and b in percent_like:
        return True
    if a in _YEAR_UNITS and b in _YEAR_UNITS:
        return True
    return False


def _in_bounds(field: str, value: Decimal) -> bool:
    spec = ASSUMPTION_BOUNDS.get(field)
    if spec is None:
        return False
    lo, hi, mode = spec
    if lo is not None:
        if mode == "open_low" and value <= lo:
            return False
        if mode != "open_low" and value < lo:
            return False
    if hi is not None:
        if mode == "open_high" and value >= hi:
            return False
        if mode != "open_high" and value > hi:
            return False
    return True


def _copy(item: CanonicalAssumption, *, status: str, detail: str, validated_by: str = "assumption_validator") -> CanonicalAssumption:
    return replace(
        item,
        validation_status=status,
        validated_by=validated_by,
        detail=detail,
        confidence=None if status != "ACCEPTED" else item.confidence,
    )


def validate_assumption(
    item: CanonicalAssumption,
    *,
    historical: Mapping[str, Decimal] | None = None,
    pack: tuple[CanonicalAssumption, ...] = (),
    required_period: str | None = None,
    required_unit: str | None = "decimal",
) -> AssumptionValidation:
    """Validate one assumption. Does not treat AI confidence as evidence."""
    _ = item.confidence
    if item.field in FACT_FIELDS:
        rejected = _copy(item, status="REJECTED", detail="facts cannot be assumptions")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if item.field in DERIVED_FIELDS or classify_data_class(item.field) != DATA_CLASS_ASSUMPTION:
        rejected = _copy(item, status="REJECTED", detail="derived values cannot become assumptions")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if item.source not in ASSUMPTION_SOURCES:
        rejected = _copy(item, status="REJECTED", detail=f"unknown assumption source {item.source}")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if item.scenario not in SCENARIOS:
        rejected = _copy(item, status="REJECTED", detail="invalid scenario")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if refuse_circular_assumption(item.field, source_fields=(item.source,)):
        rejected = _copy(item, status="REJECTED", detail="circular derived/valuation source")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    circular_reason = str(item.reasoning or "").lower()
    if any(token in circular_reason for token in CIRCULAR_ASSUMPTION_SOURCES):
        rejected = _copy(
            item,
            status="REJECTED",
            detail="assumption reasoning depends on derived valuation",
        )
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if item.value is None:
        status = "USER_REQUIRED" if item.source_is_ai_synthesis else "UNKNOWN"
        updated = _copy(item, status=status, detail="missing numeric value")
        return AssumptionValidation(updated, status, updated.detail)
    try:
        value = Decimal(item.value)
    except (InvalidOperation, ValueError, TypeError):
        rejected = _copy(item, status="REJECTED", detail="value is not numeric")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if value.is_nan() or value.is_infinite():
        rejected = _copy(item, status="REJECTED", detail="NaN/infinity is not a valid assumption")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if item.unit is None or str(item.unit).strip() == "":
        rejected = _copy(item, status="REJECTED", detail="unit required")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    expected_unit = "years" if item.field == "projection_years" else required_unit
    if expected_unit is not None and not units_compatible(item.unit, expected_unit):
        rejected = _copy(item, status="REJECTED", detail="unit incompatible")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if item.field == "projection_years" and value != value.to_integral_value():
        rejected = _copy(item, status="REJECTED", detail="projection_years must be an integer")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if not _in_bounds(item.field, value):
        rejected = _copy(item, status="REJECTED", detail="outside configured bounds")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if required_period and item.period:
        left = canonicalize_period(item.period)
        right = canonicalize_period(required_period)
        if left is not None and right is not None and not periods_comparable(left, right):
            rejected = _copy(item, status="REJECTED", detail="period mismatch")
            return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if item.source_is_ai_synthesis and not item.evidence_ids:
        rejected = _copy(
            item,
            status="REJECTED",
            detail="AI synthesis is not primary evidence",
        )
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)

    hist = historical or {}
    if item.field in {"fcf_growth_rate", "revenue_growth"} and item.field in hist:
        divergence = abs(value - hist[item.field])
        if divergence > _GROWTH_DIVERGENCE and not item.evidence_ids:
            reviewed = _copy(
                item,
                status="REVIEW_REQUIRED",
                detail="growth diverges from history without evidence",
            )
            return AssumptionValidation(reviewed, "REVIEW_REQUIRED", reviewed.detail)

    peers = [row for row in pack if row.scenario == item.scenario and row.field != item.field]
    growth = {row.field: row.value for row in peers if row.value is not None}
    growth[item.field] = value
    rev = growth.get("revenue_growth")
    fcf_g = growth.get("fcf_growth_rate")
    if rev is not None and fcf_g is not None and abs(fcf_g - rev) > _GROWTH_DIVERGENCE:
        if not item.evidence_ids:
            reviewed = _copy(
                item,
                status="REVIEW_REQUIRED",
                detail="revenue vs FCF growth divergence lacks evidence",
            )
            return AssumptionValidation(reviewed, "REVIEW_REQUIRED", reviewed.detail)

    wacc = growth.get("wacc", growth.get("discount_rate"))
    terminal = growth.get("terminal_growth_rate")
    if (
        item.field in {"wacc", "discount_rate", "terminal_growth_rate"}
        and wacc is not None
        and terminal is not None
        and wacc <= terminal
    ):
        rejected = _copy(
            item,
            status="REJECTED",
            detail="WACC must exceed terminal growth",
        )
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)

    accepted = _copy(
        item,
        status="ACCEPTED",
        detail="within bounds, typed, and not contradicted",
    )
    return AssumptionValidation(accepted, "ACCEPTED", accepted.detail)


def validate_assumption_pack(
    items: tuple[CanonicalAssumption, ...],
    *,
    historical: Mapping[str, Decimal] | None = None,
    required_period: str | None = None,
) -> tuple[AssumptionValidation, ...]:
    """Validate a scenario pack. Isolation is by scenario field on each row."""
    return tuple(
        validate_assumption(
            item,
            historical=historical,
            pack=items,
            required_period=required_period,
        )
        for item in items
    )


def ai_assumption_workflow(
    item: CanonicalAssumption,
    *,
    historical: Mapping[str, Decimal] | None = None,
    pack: tuple[CanonicalAssumption, ...] = (),
) -> AssumptionValidation:
    """DATA MISSING → AI research/proposal → validator → ACCEPT or REJECT/USER_REQUIRED."""
    proposed = replace(item, validation_status="PROPOSED")
    if classify_data_class(proposed.field) == DATA_CLASS_FACT:
        rejected = _copy(proposed, status="REJECTED", detail="AI cannot establish a financial fact")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    if classify_data_class(proposed.field) == DATA_CLASS_DERIVED:
        rejected = _copy(proposed, status="REJECTED", detail="AI cannot supply a derived result")
        return AssumptionValidation(rejected, "REJECTED", rejected.detail)
    result = validate_assumption(proposed, historical=historical, pack=pack)
    if result.status == "REJECTED" and proposed.source_is_ai_synthesis:
        user = _copy(result.assumption, status="USER_REQUIRED", detail=result.detail)
        return AssumptionValidation(user, "USER_REQUIRED", user.detail)
    return result


def million_not_equal_crore(million_amount: str, crore_amount: str) -> bool:
    """₹10,000 million is not ₹10,000 crore."""
    left = normalize_numeric_to_actual(million_amount, "million")
    right = normalize_numeric_to_actual(crore_amount, "crore")
    if left is None or right is None:
        return True
    return left != right
