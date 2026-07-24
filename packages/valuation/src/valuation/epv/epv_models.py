"""Domain models for Earnings Power Value (EPV) — research-only.

EPV estimates intrinsic enterprise value assuming **no future growth**,
capitalizing normalized sustainable earnings at the cost of capital.

References
    Greenwald, B. — Value Investing (earnings power value framework).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ScenarioOutcome,
    SensitivityMatrix,
    ValidationSummary,
    ValuationMetadata,
    ValuationResult,
)
from valuation.core.confidence_engine import ConfidenceDetail
from valuation.epv.epv_explainability import EpvExplainedValue

__all__ = [
    "EPV_VERSION",
    "RESEARCH_DISCLAIMER",
    "NormalizationMethod",
    "EpvQualityFlag",
    "EpvInputs",
    "NormalizationDetail",
    "EpvResult",
    "to_valuation_result",
    "to_v2_aggregate_payload",
]

EPV_VERSION = "0.6.0-epv"


class NormalizationMethod(str, Enum):
    """How sustainable earnings / EBIT are normalized."""

    HISTORICAL_AVERAGE = "historical_average"
    MEDIAN = "median"
    MANUAL_OVERRIDE = "manual_override"
    BUSINESS_CYCLE_ADJUSTMENT = "business_cycle_adjustment"


class EpvQualityFlag(str, Enum):
    """EPV-specific research quality / risk flags."""

    STABLE_EARNINGS = "stable_earnings"
    DECLINING_EARNINGS = "declining_earnings"
    HIGH_CYCLICALITY = "high_cyclicality"
    MARGIN_COMPRESSION = "margin_compression"
    ACCOUNTING_WARNING = "accounting_warning"
    HIGH_MAINTENANCE_CAPEX = "high_maintenance_capex"
    STRONG_OWNER_EARNINGS = "strong_owner_earnings"
    WEAK_OWNER_EARNINGS = "weak_owner_earnings"


@dataclass(frozen=True, slots=True)
class EpvInputs:
    """Inputs for zero-growth Earnings Power Value.

    Attributes:
        revenue: Current / reference revenue.
        ebit: Latest reported EBIT (pre-normalization).
        ebit_margin: Optional EBIT / revenue (used when deriving EBIT).
        tax_rate: Effective tax rate in [0, 1).
        maintenance_capex: CapEx required to sustain current earnings power.
        depreciation: D&A corresponding to the earnings base.
        working_capital_adjustment: Maintenance ΔNWC (positive = cash use).
        normalized_earnings: Optional direct override of normalized free earnings.
        cost_of_capital: WACC / discount rate for zero-growth capitalization (> 0).
        cash: Excess cash / non-operating cash.
        debt: Interest-bearing debt.
        minority_interest: Minority / NCI claim.
        investments: Non-operating investments / associates.
        shares_outstanding: Diluted shares.
        current_market_price: Optional price for MoS research posture.
        normalization_method: How to normalize EBIT / earnings.
        historical_ebit: History for average / median / cycle methods.
        historical_ebit_margin: Optional margin history.
        normalized_operating_margin: Optional margin override.
        average_ebit: Optional pre-computed average EBIT.
        average_ebit_margin: Optional pre-computed average margin.
        cycle_adjustment_factor: Multiplier for cycle adjustment (default 1.0).
        one_time_gains: Add-backs removed from normalized EBIT (positive = remove).
        one_time_losses: Losses added back (positive magnitude added).
        asset_sales: Gains from asset sales to remove.
        exceptional_items: Net exceptional items to remove (signed).
        accounting_distortions: Signed adjustments to reverse distortions.
        accounting_quality_score: Optional 0–1 or 0–100 research input.
        bear_earnings_delta: Additive delta to normalized free earnings (bear).
        bull_earnings_delta: Additive delta (bull).
        bear_wacc_delta: Additive WACC delta for bear.
        bull_wacc_delta: Additive WACC delta for bull.
    """

    revenue: float
    ebit: float
    tax_rate: float
    maintenance_capex: float
    depreciation: float
    cost_of_capital: float
    shares_outstanding: float
    ebit_margin: float | None = None
    working_capital_adjustment: float = 0.0
    normalized_earnings: float | None = None
    cash: float = 0.0
    debt: float = 0.0
    minority_interest: float = 0.0
    investments: float = 0.0
    current_market_price: float | None = None
    currency: str = "USD"
    normalization_method: NormalizationMethod = NormalizationMethod.MANUAL_OVERRIDE
    historical_ebit: tuple[float, ...] = ()
    historical_ebit_margin: tuple[float, ...] = ()
    normalized_operating_margin: float | None = None
    average_ebit: float | None = None
    average_ebit_margin: float | None = None
    cycle_adjustment_factor: float = 1.0
    one_time_gains: float = 0.0
    one_time_losses: float = 0.0
    asset_sales: float = 0.0
    exceptional_items: float = 0.0
    accounting_distortions: float = 0.0
    accounting_quality_score: float | None = None
    bear_earnings_delta: float = 0.0
    bull_earnings_delta: float = 0.0
    bear_wacc_delta: float = 0.01
    bull_wacc_delta: float = -0.01


@dataclass(frozen=True, slots=True)
class NormalizationDetail:
    """Transparent normalization trail."""

    method: NormalizationMethod
    raw_ebit: float
    normalized_ebit: float
    adjustments: Mapping[str, float]
    notes: str = ""


@dataclass(frozen=True, slots=True)
class EpvResult:
    """Full EPV research result."""

    version: str
    currency: str
    disclaimer: str
    methodology: str
    normalization: NormalizationDetail
    normalized_ebit: EpvExplainedValue
    tax_adjusted_ebit: EpvExplainedValue
    maintenance_capex: EpvExplainedValue
    owner_earnings: EpvExplainedValue
    normalized_free_earnings: EpvExplainedValue
    enterprise_epv: EpvExplainedValue
    equity_value: EpvExplainedValue
    intrinsic_value: EpvExplainedValue
    intrinsic_value_per_share: EpvExplainedValue
    margin_of_safety: EpvExplainedValue
    confidence: str
    confidence_detail: ConfidenceDetail
    quality_flags: tuple[EpvQualityFlag, ...]
    core_quality_flags: tuple[QualityFlag, ...]
    validation_summary: ValidationSummary
    scenarios: tuple[ScenarioOutcome, ...]
    sensitivity: SensitivityMatrix
    explainability: tuple[EpvExplainedValue, ...]
    limitations: tuple[str, ...]
    metadata: ValuationMetadata
    execution_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for research consumers."""
        return {
            "version": self.version,
            "currency": self.currency,
            "disclaimer": self.disclaimer,
            "methodology": self.methodology,
            "normalized_ebit": self.normalized_ebit.value,
            "tax_adjusted_ebit": self.tax_adjusted_ebit.value,
            "owner_earnings": self.owner_earnings.value,
            "normalized_free_earnings": self.normalized_free_earnings.value,
            "enterprise_epv": self.enterprise_epv.value,
            "equity_value": self.equity_value.value,
            "intrinsic_value": self.intrinsic_value.value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share.value,
            "margin_of_safety": self.margin_of_safety.value,
            "confidence": self.confidence,
            "quality_flags": [f.value for f in self.quality_flags],
            "execution_time_ms": self.execution_time_ms,
        }


def to_valuation_result(result: EpvResult) -> ValuationResult:
    """Map EPV onto the shared :class:`ValuationResult`."""
    return ValuationResult(
        model_name="epv",
        version=result.version,
        methodology=result.methodology,
        intrinsic_value=result.intrinsic_value.value,
        enterprise_value=result.enterprise_epv.value,
        equity_value=result.equity_value.value,
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


def to_v2_aggregate_payload(result: EpvResult) -> dict[str, object]:
    """Stable cite payload for future V2.0 valuation aggregation."""
    return {
        "method": "epv",
        "module": "valuation.epv",
        "version": result.version,
        "currency": result.currency,
        "enterprise_epv": result.enterprise_epv.value,
        "equity_value": result.equity_value.value,
        "intrinsic_value_per_share": result.intrinsic_value_per_share.value,
        "confidence": result.confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "disclaimer": result.disclaimer,
        "core_version": VALUATION_CORE_VERSION,
    }
