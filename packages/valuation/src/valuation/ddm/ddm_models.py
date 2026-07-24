"""Domain models for Dividend Discount Model (DDM) — research-only.

Supports zero-growth, Gordon (single-stage), two-stage, and multi-stage DDM.
Assumptions and limitations must be stated explicitly.

References
    Gordon growth model; Damodaran multi-stage dividend discount models.
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
from valuation.ddm.ddm_explainability import DdmExplainedValue

__all__ = [
    "DDM_VERSION",
    "RESEARCH_DISCLAIMER",
    "DdmMethod",
    "DividendQuality",
    "DdmQualityFlag",
    "DdmInputs",
    "DividendYear",
    "DdmResult",
    "to_valuation_result",
    "to_v2_aggregate_payload",
]

DDM_VERSION = "0.8.0-ddm"


class DdmMethod(str, Enum):
    """Which DDM variant to apply."""

    ZERO_GROWTH = "zero_growth"
    GORDON = "gordon"
    TWO_STAGE = "two_stage"
    MULTI_STAGE = "multi_stage"


class DividendQuality(str, Enum):
    """Research dividend-quality grade."""

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    WEAK = "weak"


class DdmQualityFlag(str, Enum):
    """DDM-specific research quality / risk flags."""

    DIVIDEND_ARISTOCRAT = "dividend_aristocrat"
    HIGH_PAYOUT = "high_payout"
    UNSUSTAINABLE_DIVIDEND = "unsustainable_dividend"
    LOW_COVERAGE = "low_coverage"
    DIVIDEND_CUT_RISK = "dividend_cut_risk"
    HIGH_GROWTH_ASSUMPTION = "high_growth_assumption"
    NEGATIVE_GROWTH = "negative_growth"
    WEAK_CASH_FLOW = "weak_cash_flow"
    STRONG_DIVIDEND_HISTORY = "strong_dividend_history"


@dataclass(frozen=True, slots=True)
class DdmInputs:
    """Inputs for Dividend Discount Model valuation.

    Attributes:
        current_dps: Last paid / trailing dividend per share (D₀).
        cost_of_equity: Required equity return r (> 0).
        method: Which DDM variant to run.
        expected_dividend_growth: Stage-1 / Gordon growth g (decimal).
        terminal_growth: Perpetual growth after explicit horizon (decimal).
        forecast_years: Explicit years for two-stage / multi-stage.
        dividend_growth_schedule: Per-year growth rates for multi-stage
            (length = forecast_years). If omitted in multi-stage, falls back
            to expected_dividend_growth for each year.
        shares_outstanding: Diluted shares (for firm equity IV).
        current_market_price: Price for MoS research posture.
        dividend_payout_ratio: Optional payout (Div/NI).
        retention_ratio: Optional retention; if set with ROE may imply g.
        roe: Optional ROE (with retention → implied growth).
        eps: Optional EPS for coverage / implied DPS checks.
        book_value: Optional book equity (research context).
        historical_dividend_cagr: Optional historical CAGR for quality.
        dividend_stability_score: Optional 0–1 or 0–100 research score.
        dividend_coverage_ratio: Optional earnings/FCF coverage of dividends.
        free_cash_flow_payout_ratio: Optional FCF payout.
        years_of_dividend_growth: Optional consecutive growth years
            (aristocrat research signal when ≥ 25).
        bear_growth_delta / bull_growth_delta: Scenario overlays on g.
        bear_coe_delta / bull_coe_delta: Scenario overlays on cost of equity.
    """

    current_dps: float
    cost_of_equity: float
    method: DdmMethod = DdmMethod.GORDON
    expected_dividend_growth: float = 0.03
    terminal_growth: float = 0.02
    forecast_years: int = 5
    dividend_growth_schedule: tuple[float, ...] = ()
    shares_outstanding: float = 1.0
    current_market_price: float | None = None
    dividend_payout_ratio: float | None = None
    retention_ratio: float | None = None
    roe: float | None = None
    eps: float | None = None
    book_value: float | None = None
    historical_dividend_cagr: float | None = None
    dividend_stability_score: float | None = None
    dividend_coverage_ratio: float | None = None
    free_cash_flow_payout_ratio: float | None = None
    years_of_dividend_growth: int | None = None
    accounting_quality_score: float | None = None
    currency: str = "USD"
    bear_growth_delta: float = -0.01
    bull_growth_delta: float = 0.01
    bear_coe_delta: float = 0.01
    bull_coe_delta: float = -0.01


@dataclass(frozen=True, slots=True)
class DividendYear:
    """One explicit forecast year of dividends."""

    year: int
    growth: float
    dividend: float
    present_value: float
    explained: DdmExplainedValue


@dataclass(frozen=True, slots=True)
class DdmResult:
    """Full DDM research result."""

    version: str
    currency: str
    disclaimer: str
    methodology: str
    method_used: DdmMethod
    forecast_dividends: tuple[DividendYear, ...]
    terminal_dividend: DdmExplainedValue
    present_value_dividends: DdmExplainedValue
    terminal_value: DdmExplainedValue
    terminal_value_pv: DdmExplainedValue
    intrinsic_value_per_share: DdmExplainedValue
    intrinsic_value: DdmExplainedValue
    margin_of_safety: DdmExplainedValue
    dividend_yield: DdmExplainedValue
    payout_ratio: DdmExplainedValue
    dividend_quality: DividendQuality
    confidence: str
    confidence_detail: ConfidenceDetail
    quality_flags: tuple[DdmQualityFlag, ...]
    core_quality_flags: tuple[QualityFlag, ...]
    validation_summary: ValidationSummary
    scenarios: tuple[ScenarioOutcome, ...]
    sensitivity: SensitivityMatrix
    explainability: tuple[DdmExplainedValue, ...]
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
            "terminal_dividend": self.terminal_dividend.value,
            "present_value_dividends": self.present_value_dividends.value,
            "terminal_value": self.terminal_value.value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share.value,
            "intrinsic_value": self.intrinsic_value.value,
            "margin_of_safety": self.margin_of_safety.value,
            "dividend_yield": self.dividend_yield.value,
            "payout_ratio": self.payout_ratio.value,
            "dividend_quality": self.dividend_quality.value,
            "confidence": self.confidence,
            "quality_flags": [f.value for f in self.quality_flags],
            "execution_time_ms": self.execution_time_ms,
        }


def to_valuation_result(result: DdmResult) -> ValuationResult:
    """Map DDM onto the shared :class:`ValuationResult`."""
    return ValuationResult(
        model_name="ddm",
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


def to_v2_aggregate_payload(result: DdmResult) -> dict[str, object]:
    """Stable cite payload for future V2.0 valuation aggregation."""
    return {
        "method": "ddm",
        "module": "valuation.ddm",
        "version": result.version,
        "currency": result.currency,
        "ddm_method": result.method_used.value,
        "intrinsic_value_per_share": result.intrinsic_value_per_share.value,
        "intrinsic_value": result.intrinsic_value.value,
        "dividend_quality": result.dividend_quality.value,
        "confidence": result.confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "disclaimer": result.disclaimer,
        "core_version": VALUATION_CORE_VERSION,
    }
