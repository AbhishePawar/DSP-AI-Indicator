"""Domain models for Benjamin Graham Intrinsic Value — research-only.

Heuristic formulas (original and revised / “modern”) for educational research.
Assumptions must be stated explicitly; not a recommendation engine.

References
    Graham, B. — The Intelligent Investor (intrinsic value heuristics).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from valuation.core.confidence_engine import ConfidenceDetail
from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioOutcome,
    SensitivityMatrix,
    ValidationSummary,
    ValuationMetadata,
    ValuationResult,
)
from valuation.graham.graham_explainability import GrahamExplainedValue

__all__ = [
    "GRAHAM_VERSION",
    "RESEARCH_DISCLAIMER",
    "GrahamFormula",
    "GrahamQualityFlag",
    "GrahamInputs",
    "GrahamResult",
    "to_valuation_result",
    "to_v2_aggregate_payload",
]

GRAHAM_VERSION = "0.7.0-graham"

DEFAULT_REFERENCE_AAA_YIELD = 0.044  # classic Graham reference ~4.4%


class GrahamFormula(str, Enum):
    """Which Graham heuristic to apply."""

    ORIGINAL = "original"
    MODERN = "modern"


class GrahamQualityFlag(str, Enum):
    """Graham-specific research quality / risk flags."""

    STABLE_EARNINGS = "stable_earnings"
    CYCLICAL_EARNINGS = "cyclical_earnings"
    NEGATIVE_EPS = "negative_eps"
    LOW_BOOK_VALUE = "low_book_value"
    HIGH_GROWTH_ASSUMPTION = "high_growth_assumption"
    ACCOUNTING_WARNING = "accounting_warning"
    LOW_CONFIDENCE = "low_confidence"


@dataclass(frozen=True, slots=True)
class GrahamInputs:
    """Inputs for Graham intrinsic-value heuristics.

    Attributes:
        eps_trailing: Trailing twelve-month EPS.
        growth_rate: Expected annual EPS growth as a percent number
            (e.g. ``7`` means 7%, matching Graham's published form)
            OR as a decimal if ``growth_as_decimal`` is True.
        aaa_bond_yield: Current AAA corporate bond yield (decimal, e.g. 0.05).
        shares_outstanding: Diluted shares.
        formula: Original vs modern (yield-adjusted) Graham formula.
        normalized_eps: Optional normalized EPS override (preferred when set).
        book_value_per_share: Optional BVPS for quality flags / research.
        required_return: Optional required return (research context; not in
            classic Graham IV formula).
        current_market_price: Price for MoS research posture.
        cash: Firm cash (optional; for equity context notes).
        debt: Firm debt (optional).
        reference_aaa_yield: Modern formula numerator (default 4.4%).
        growth_as_decimal: If True, ``growth_rate`` is 0.07 for 7%.
        average_eps_3y / 5y / 10y: Optional averages for stability scoring.
        normalized_roe: Optional ROE research input.
        accounting_quality_score: Optional 0–1 or 0–100.
        allow_negative_eps: If False (default), negative EPS is rejected.
        bear_growth_delta / bull_growth_delta: Scenario overlays on G
            (same units as growth_rate).
        bear_yield_delta / bull_yield_delta: Scenario overlays on AAA yield.
    """

    eps_trailing: float
    growth_rate: float
    aaa_bond_yield: float
    shares_outstanding: float = 1.0
    formula: GrahamFormula = GrahamFormula.MODERN
    normalized_eps: float | None = None
    book_value_per_share: float | None = None
    required_return: float | None = None
    current_market_price: float | None = None
    cash: float = 0.0
    debt: float = 0.0
    reference_aaa_yield: float = DEFAULT_REFERENCE_AAA_YIELD
    growth_as_decimal: bool = False
    average_eps_3y: float | None = None
    average_eps_5y: float | None = None
    average_eps_10y: float | None = None
    normalized_roe: float | None = None
    accounting_quality_score: float | None = None
    allow_negative_eps: bool = False
    currency: str = "USD"
    bear_growth_delta: float = -1.0
    bull_growth_delta: float = 1.0
    bear_yield_delta: float = 0.005
    bull_yield_delta: float = -0.005


@dataclass(frozen=True, slots=True)
class GrahamResult:
    """Full Graham intrinsic-value research result."""

    version: str
    currency: str
    disclaimer: str
    methodology: str
    method_used: GrahamFormula
    eps_used: GrahamExplainedValue
    growth_assumption: GrahamExplainedValue
    reference_yield: GrahamExplainedValue
    current_yield: GrahamExplainedValue
    intrinsic_value_per_share: GrahamExplainedValue
    intrinsic_value: GrahamExplainedValue
    margin_of_safety: GrahamExplainedValue
    required_return: GrahamExplainedValue
    confidence: str
    confidence_detail: ConfidenceDetail
    quality_flags: tuple[GrahamQualityFlag, ...]
    core_quality_flags: tuple[QualityFlag, ...]
    validation_summary: ValidationSummary
    scenarios: tuple[ScenarioOutcome, ...]
    sensitivity: SensitivityMatrix
    explainability: tuple[GrahamExplainedValue, ...]
    limitations: tuple[str, ...]
    metadata: ValuationMetadata
    execution_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "currency": self.currency,
            "disclaimer": self.disclaimer,
            "methodology": self.methodology,
            "method_used": self.method_used.value,
            "eps_used": self.eps_used.value,
            "growth_assumption": self.growth_assumption.value,
            "reference_yield": self.reference_yield.value,
            "current_yield": self.current_yield.value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share.value,
            "intrinsic_value": self.intrinsic_value.value,
            "margin_of_safety": self.margin_of_safety.value,
            "confidence": self.confidence,
            "quality_flags": [f.value for f in self.quality_flags],
            "execution_time_ms": self.execution_time_ms,
        }


def to_valuation_result(result: GrahamResult) -> ValuationResult:
    """Map Graham onto the shared :class:`ValuationResult`."""
    return ValuationResult(
        model_name="graham",
        version=result.version,
        methodology=result.methodology,
        intrinsic_value=result.intrinsic_value.value,
        enterprise_value=None,
        equity_value=result.intrinsic_value.value,
        intrinsic_value_per_share=result.intrinsic_value_per_share.value,
        margin_of_safety=result.margin_of_safety.value,
        confidence_score=result.confidence_detail.score,
        confidence_level=result.confidence_detail.level,
        quality_flags=result.core_quality_flags,
        sensitivity_results=result.sensitivity,
        scenario_results=result.scenarios,
        validation_summary=result.validation_summary,
        explainability=result.explainability,
        research_disclaimer=result.disclaimer,
        execution_time_ms=result.execution_time_ms,
        metadata=result.metadata,
        currency=result.currency,
        confidence_explanation=result.confidence_detail.explanation,
    )


def to_v2_aggregate_payload(result: GrahamResult) -> dict[str, object]:
    """Stable cite payload for future V2.0 valuation aggregation."""
    return {
        "method": "graham",
        "module": "valuation.graham",
        "version": result.version,
        "currency": result.currency,
        "formula": result.method_used.value,
        "intrinsic_value_per_share": result.intrinsic_value_per_share.value,
        "intrinsic_value": result.intrinsic_value.value,
        "confidence": result.confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "disclaimer": result.disclaimer,
        "core_version": VALUATION_CORE_VERSION,
    }
