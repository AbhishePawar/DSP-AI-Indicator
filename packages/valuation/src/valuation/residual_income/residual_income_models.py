"""Domain models for Residual Income Valuation (research-only).

References
    Penman, S. — Financial Statement Analysis and Security Valuation
    (residual income / clean-surplus framework).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from valuation.residual_income.residual_income_explainability import RiExplainedValue

__all__ = [
    "RESIDUAL_INCOME_VERSION",
    "RESEARCH_DISCLAIMER",
    "RoeForecastModel",
    "ResidualIncomeScenario",
    "RiQualityFlag",
    "ResidualIncomeInputs",
    "ResidualIncomeYear",
    "CleanSurplusCheck",
    "RiSensitivityCell",
    "RiSensitivityMatrix",
    "RiScenarioResult",
    "RiValidationSummary",
    "RiConfidenceDetail",
    "ResidualIncomeResult",
    "to_v2_aggregate_payload",
]

RESIDUAL_INCOME_VERSION = "0.4.1-residual-income"

RESEARCH_DISCLAIMER = (
    "This valuation is intended for research and educational purposes only. "
    "It is not investment advice or a Buy/Sell recommendation."
)


class RoeForecastModel(str, Enum):
    """How period ROE is projected through the explicit horizon.

    * ``CONSTANT`` — ROE_t = roe_forecast for all t
    * ``LINEAR_FADE`` — linear interpolation from roe_forecast to terminal_roe
    * ``MEAN_REVERSION`` — exponential fade toward ``roe_long_run``
    * ``MANUAL`` — use ``roe_manual_series`` (length = forecast_years)
    """

    CONSTANT = "constant"
    LINEAR_FADE = "linear_fade"
    MEAN_REVERSION = "mean_reversion"
    MANUAL = "manual"


class ResidualIncomeScenario(str, Enum):
    """Independent scenario labels (ROE overlay)."""

    BEAR = "bear"
    BASE = "base"
    BULL = "bull"


class RiQualityFlag(str, Enum):
    """Research quality / risk flags (not recommendations)."""

    HIGH_ROE_SUSTAINABILITY = "high_roe_sustainability"
    DECLINING_ROE = "declining_roe"
    NEGATIVE_RESIDUAL_INCOME = "negative_residual_income"
    WEAK_BOOK_VALUE_GROWTH = "weak_book_value_growth"
    ACCOUNTING_WARNING = "accounting_warning"
    CAPITAL_EFFICIENT_BUSINESS = "capital_efficient_business"
    CLEAN_SURPLUS_WARNING = "clean_surplus_warning"


@dataclass(frozen=True, slots=True)
class ResidualIncomeInputs:
    """Inputs for multi-period residual income valuation.

    Book value is projected automatically via clean surplus:
    ``BV_t = BV_{t−1} + NI_t − Div_t``. Callers supply only ``current_book_value``
    (BV_0), not a yearly BV series.

    Attributes:
        current_book_value: Opening book equity (must be > 0).
        roe_forecast: Starting / constant ROE (decimal).
        cost_of_equity: Required return r (decimal, > 0).
        net_income_forecast: Optional year-1 NI override (constant/base only).
        dividend_payout_ratio: Div_t / NI_t when retention not set.
        retention_ratio: If set, overrides payout as ``1 − retention``.
        forecast_years: Explicit horizon (default 10).
        terminal_roe: Long-run ROE for fade / continuing RI (optional).
        terminal_growth: Perpetual growth g for continuing value (g < r).
        shares_outstanding: Shares for per-share IV.
        current_market_price: Optional price for MoS research posture.
        roe_model: ROE path model (see :class:`RoeForecastModel`).
        roe_long_run: Mean-reversion target (defaults to terminal_roe or roe).
        mean_reversion_kappa: Speed in (0, 1] for mean reversion.
        roe_manual_series: Manual ROE per year when model is MANUAL.
        accounting_quality_score: Optional 0–100 research input.
        historical_roe_series: Optional history for stability scoring.
    """

    current_book_value: float
    roe_forecast: float
    cost_of_equity: float
    net_income_forecast: float | None = None
    dividend_payout_ratio: float = 0.40
    retention_ratio: float | None = None
    forecast_years: int = 10
    terminal_roe: float | None = None
    terminal_growth: float = 0.02
    shares_outstanding: float = 1.0
    current_market_price: float | None = None
    currency: str = "USD"
    bear_roe_delta: float = -0.02
    bull_roe_delta: float = 0.02
    roe_model: RoeForecastModel = RoeForecastModel.CONSTANT
    roe_long_run: float | None = None
    mean_reversion_kappa: float = 0.30
    roe_manual_series: tuple[float, ...] | None = None
    accounting_quality_score: float | None = None
    historical_roe_series: tuple[float, ...] = ()


@dataclass(frozen=True, slots=True)
class CleanSurplusCheck:
    """Per-year clean-surplus identity check.

    Identity: ``BV_{t−1} + NI_t − Div_t = BV_t``.
    """

    year: int
    opening_book_value: float
    net_income: float
    dividends: float
    ending_book_value: float
    implied_ending: float
    residual: float
    ok: bool


@dataclass(frozen=True, slots=True)
class ResidualIncomeYear:
    """One explicit forecast year with automatic BV projection."""

    year: int
    roe: float
    opening_book_value: float
    net_income: float
    dividends: float
    ending_book_value: float
    residual_income: float
    cost_of_equity_charge: float
    present_value_ri: float
    clean_surplus: CleanSurplusCheck
    explained: RiExplainedValue


@dataclass(frozen=True, slots=True)
class RiSensitivityCell:
    """One OTAT sensitivity cell."""

    dimension: str
    parameter_value: float
    intrinsic_equity_value: float | None
    intrinsic_value_per_share: float | None


@dataclass(frozen=True, slots=True)
class RiSensitivityMatrix:
    """Sensitivity grids for research (deterministic)."""

    roe: tuple[RiSensitivityCell, ...]
    cost_of_equity: tuple[RiSensitivityCell, ...]
    terminal_growth: tuple[RiSensitivityCell, ...]
    payout_ratio: tuple[RiSensitivityCell, ...]
    terminal_roe: tuple[RiSensitivityCell, ...]
    explained: RiExplainedValue


@dataclass(frozen=True, slots=True)
class RiScenarioResult:
    """Independent reverse-path scenario result."""

    scenario: ResidualIncomeScenario
    intrinsic_equity_value: RiExplainedValue
    intrinsic_value_per_share: RiExplainedValue
    pv_residual_income: RiExplainedValue
    continuing_value: RiExplainedValue
    margin_of_safety: RiExplainedValue
    confidence: str


@dataclass(frozen=True, slots=True)
class RiValidationSummary:
    """Structured validation outcome."""

    ok: bool
    checks: tuple[str, ...]
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RiConfidenceDetail:
    """Transparent confidence rationale for research consumers."""

    level: str
    score: int
    max_score: int
    factors: Mapping[str, int]
    rationale: str


@dataclass(frozen=True, slots=True)
class ResidualIncomeResult:
    """Full residual-income research result (base scenario primary).

    Designed so V2.0 valuation aggregation can consume
    :func:`to_v2_aggregate_payload` without modifying this module.
    """

    version: str
    currency: str
    disclaimer: str
    book_value: RiExplainedValue
    years: tuple[ResidualIncomeYear, ...]
    pv_residual_income: RiExplainedValue
    continuing_value: RiExplainedValue
    continuing_value_pv: RiExplainedValue
    intrinsic_equity_value: RiExplainedValue
    intrinsic_value_per_share: RiExplainedValue
    margin_of_safety: RiExplainedValue
    confidence: str
    confidence_detail: RiConfidenceDetail
    quality_flags: tuple[RiQualityFlag, ...]
    clean_surplus_ok: bool
    clean_surplus_warnings: tuple[str, ...]
    validation_summary: RiValidationSummary
    scenarios: tuple[RiScenarioResult, ...]
    sensitivity: RiSensitivityMatrix
    explainability: tuple[RiExplainedValue, ...]
    methodology: str
    limitations: tuple[str, ...]
    roe_model: RoeForecastModel
    stages: Mapping[str, str]


def to_v2_aggregate_payload(result: ResidualIncomeResult) -> dict[str, object]:
    """Stable cite payload for future V2.0 valuation aggregation.

    Does not embed aggregates; consumers may hold ids / digests / values.
    """
    return {
        "method": "residual_income",
        "module": "valuation.residual_income",
        "version": result.version,
        "currency": result.currency,
        "intrinsic_equity_value": result.intrinsic_equity_value.value,
        "intrinsic_value_per_share": result.intrinsic_value_per_share.value,
        "confidence": result.confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "clean_surplus_ok": result.clean_surplus_ok,
        "disclaimer": result.disclaimer,
        "stages": dict(result.stages),
    }
