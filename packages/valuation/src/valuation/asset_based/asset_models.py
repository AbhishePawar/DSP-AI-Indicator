"""Domain models for Asset-Based & Liquidation Valuation — research-only.

Supports book value, tangible book, NAV, adjusted NAV, liquidation,
conservative liquidation, and replacement cost.

References
    Damodaran asset-based approaches; liquidation / NAV research heuristics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

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
from valuation.asset_based.asset_explainability import AssetExplainedValue

__all__ = [
    "ASSET_BASED_VERSION",
    "RESEARCH_DISCLAIMER",
    "AssetMethod",
    "AssetQuality",
    "AssetQualityFlag",
    "HaircutSchedule",
    "AssetBasedInputs",
    "AssetAdjustment",
    "AssetValuationResult",
    "DEFAULT_CONSERVATIVE_HAIRCUTS",
    "to_valuation_result",
    "to_v2_aggregate_payload",
]

ASSET_BASED_VERSION = "0.9.0-asset-based"

# Recovery rates (fraction of carrying / fair value retained in liquidation).
DEFAULT_CONSERVATIVE_HAIRCUTS: Mapping[str, float] = {
    "cash": 1.0,
    "cash_equivalents": 1.0,
    "investments": 1.0,  # mark-to-market assumed; override via schedule
    "receivables": 0.80,
    "inventory": 0.50,
    "biological_assets": 0.40,
    "ppe": 0.40,
    "investment_property": 0.60,
    "intangible_assets": 0.0,
    "goodwill": 0.0,
    "deferred_tax_assets": 0.0,
    "other_assets": 0.30,
}


class AssetMethod(str, Enum):
    """Which asset-based method to run as the primary intrinsic value."""

    BOOK_VALUE = "book_value"
    TANGIBLE_BOOK = "tangible_book"
    NAV = "nav"
    ADJUSTED_NAV = "adjusted_nav"
    LIQUIDATION = "liquidation"
    CONSERVATIVE_LIQUIDATION = "conservative_liquidation"
    REPLACEMENT_COST = "replacement_cost"


class AssetQuality(str, Enum):
    """Research asset-quality grade."""

    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    WEAK = "weak"


class AssetQualityFlag(str, Enum):
    """Asset-based research quality / risk flags."""

    ASSET_RICH = "asset_rich"
    CASH_RICH = "cash_rich"
    HIDDEN_ASSETS = "hidden_assets"
    HIGH_INTANGIBLE_RISK = "high_intangible_risk"
    GOODWILL_HEAVY = "goodwill_heavy"
    INVENTORY_HEAVY = "inventory_heavy"
    REAL_ESTATE_UPSIDE = "real_estate_upside"
    NEGATIVE_EQUITY = "negative_equity"
    WEAK_ASSET_COVERAGE = "weak_asset_coverage"
    HIGH_LEVERAGE = "high_leverage"


@dataclass(frozen=True, slots=True)
class HaircutSchedule:
    """Category recovery rates for liquidation methods (0–1)."""

    cash: float = 1.0
    cash_equivalents: float = 1.0
    investments: float = 1.0
    receivables: float = 0.80
    inventory: float = 0.50
    biological_assets: float = 0.40
    ppe: float = 0.40
    investment_property: float = 0.60
    intangible_assets: float = 0.0
    goodwill: float = 0.0
    deferred_tax_assets: float = 0.0
    other_assets: float = 0.30

    def as_mapping(self) -> dict[str, float]:
        return {
            "cash": self.cash,
            "cash_equivalents": self.cash_equivalents,
            "investments": self.investments,
            "receivables": self.receivables,
            "inventory": self.inventory,
            "biological_assets": self.biological_assets,
            "ppe": self.ppe,
            "investment_property": self.investment_property,
            "intangible_assets": self.intangible_assets,
            "goodwill": self.goodwill,
            "deferred_tax_assets": self.deferred_tax_assets,
            "other_assets": self.other_assets,
        }


@dataclass(frozen=True, slots=True)
class AssetBasedInputs:
    """Inputs for asset-based / liquidation valuation."""

    cash: float = 0.0
    cash_equivalents: float = 0.0
    investments: float = 0.0
    receivables: float = 0.0
    inventory: float = 0.0
    biological_assets: float = 0.0
    ppe: float = 0.0
    investment_property: float = 0.0
    intangible_assets: float = 0.0
    goodwill: float = 0.0
    deferred_tax_assets: float = 0.0
    other_assets: float = 0.0
    total_assets: float | None = None

    accounts_payable: float = 0.0
    short_term_debt: float = 0.0
    long_term_debt: float = 0.0
    lease_liabilities: float = 0.0
    deferred_tax_liabilities: float = 0.0
    other_liabilities: float = 0.0
    minority_interest: float = 0.0
    preferred_equity: float = 0.0

    shares_outstanding: float = 1.0
    current_market_price: float | None = None
    method: AssetMethod = AssetMethod.BOOK_VALUE

    # Fair-value / ANAV overlays (absolute fair values; None → use carrying)
    fv_investments: float | None = None
    fv_ppe: float | None = None
    fv_investment_property: float | None = None
    fv_biological_assets: float | None = None
    fv_inventory: float | None = None
    fv_receivables: float | None = None
    independent_appraisal: float | None = None
    replacement_cost: float | None = None
    hidden_assets: float = 0.0
    off_balance_sheet_assets: float = 0.0
    off_balance_sheet_liabilities: float = 0.0
    private_holdings_adjustment: float = 0.0
    real_estate_appreciation: float = 0.0
    haircut_schedule: HaircutSchedule = field(default_factory=HaircutSchedule)
    allow_negative_equity: bool = False
    accounting_quality_score: float | None = None
    currency: str = "USD"

    # Scenario deltas (fractional haircut / appreciation overlays)
    bear_haircut_delta: float = -0.10
    bull_haircut_delta: float = 0.10
    bear_property_delta: float = -0.05
    bull_property_delta: float = 0.05


@dataclass(frozen=True, slots=True)
class AssetAdjustment:
    """One explained fair-value / liquidation adjustment."""

    name: str
    carrying_value: float
    adjusted_value: float
    delta: float
    rationale: str


@dataclass(frozen=True, slots=True)
class AssetValuationResult:
    """Full asset-based research result."""

    version: str
    currency: str
    disclaimer: str
    methodology: str
    method_used: AssetMethod
    book_value: AssetExplainedValue
    book_value_per_share: AssetExplainedValue
    tangible_book_value: AssetExplainedValue
    tangible_book_value_per_share: AssetExplainedValue
    nav: AssetExplainedValue
    nav_per_share: AssetExplainedValue
    adjusted_nav: AssetExplainedValue
    adjusted_nav_per_share: AssetExplainedValue
    liquidation_value: AssetExplainedValue
    liquidation_value_per_share: AssetExplainedValue
    conservative_liquidation_value: AssetExplainedValue
    replacement_cost_value: AssetExplainedValue
    intrinsic_value: AssetExplainedValue
    intrinsic_value_per_share: AssetExplainedValue
    margin_of_safety: AssetExplainedValue
    asset_quality: AssetQuality
    haircuts_applied: Mapping[str, float]
    adjustments: tuple[AssetAdjustment, ...]
    confidence: str
    confidence_detail: ConfidenceDetail
    quality_flags: tuple[AssetQualityFlag, ...]
    core_quality_flags: tuple[QualityFlag, ...]
    validation_summary: ValidationSummary
    scenarios: tuple[ScenarioOutcome, ...]
    sensitivity: SensitivityMatrix
    explainability: tuple[AssetExplainedValue, ...]
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
            "book_value": self.book_value.value,
            "tangible_book_value": self.tangible_book_value.value,
            "nav": self.nav.value,
            "adjusted_nav": self.adjusted_nav.value,
            "liquidation_value": self.liquidation_value.value,
            "conservative_liquidation_value": self.conservative_liquidation_value.value,
            "replacement_cost": self.replacement_cost_value.value,
            "intrinsic_value": self.intrinsic_value.value,
            "intrinsic_value_per_share": self.intrinsic_value_per_share.value,
            "margin_of_safety": self.margin_of_safety.value,
            "asset_quality": self.asset_quality.value,
            "haircuts_applied": dict(self.haircuts_applied),
            "confidence": self.confidence,
            "quality_flags": [f.value for f in self.quality_flags],
            "execution_time_ms": self.execution_time_ms,
        }


def to_valuation_result(result: AssetValuationResult) -> ValuationResult:
    """Map asset-based result onto shared :class:`ValuationResult`."""
    return ValuationResult(
        model_name="asset_based",
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


def to_v2_aggregate_payload(result: AssetValuationResult) -> dict[str, object]:
    """Stable cite payload for future V2.0 valuation aggregation."""
    return {
        "method": "asset_based",
        "module": "valuation.asset_based",
        "version": result.version,
        "currency": result.currency,
        "asset_method": result.method_used.value,
        "intrinsic_value": result.intrinsic_value.value,
        "intrinsic_value_per_share": result.intrinsic_value_per_share.value,
        "asset_quality": result.asset_quality.value,
        "confidence": result.confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "disclaimer": result.disclaimer,
        "core_version": VALUATION_CORE_VERSION,
    }
