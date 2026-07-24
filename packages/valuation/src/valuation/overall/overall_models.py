"""Domain models for Overall Valuation Aggregator — research-only.

Consumes completed :class:`~valuation.core.result_models.ValuationResult`,
V2 aggregate payloads, and/or :class:`~valuation.consensus.ConsensusResult`.
Never executes valuation engines. Research labels only — not advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from valuation.consensus.consensus_models import (
    ConsensusResult,
    MethodWeightDetail,
    SensitivitySummary,
)
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
from valuation.exceptions import ValuationError
from valuation.overall.overall_explainability import OverallExplainedValue

__all__ = [
    "OVERALL_VERSION",
    "RESEARCH_DISCLAIMER",
    "OverallValuationError",
    "MosClassification",
    "ResearchLabel",
    "OverallQualityFlag",
    "MosThresholds",
    "MethodSummaryRow",
    "ConsistencySummary",
    "ScenarioSummary",
    "OverallSensitivitySummary",
    "OverallInputs",
    "OverallValuationResult",
    "to_valuation_result",
    "to_v2_aggregate_payload",
]

OVERALL_VERSION = "0.12.0-overall"


class OverallValuationError(ValuationError):
    """Raised when overall valuation inputs fail hard validation."""


class MosClassification(str, Enum):
    """Margin-of-safety band (research classification only)."""

    DEEP_VALUE = "deep_value"
    UNDERVALUED = "undervalued"
    FAIRLY_VALUED = "fairly_valued"
    OVERVALUED = "overvalued"
    EXTREMELY_OVERVALUED = "extremely_overvalued"


class ResearchLabel(str, Enum):
    """Research posture label — NOT an investment recommendation."""

    STRONG_BUY_CANDIDATE = "strong_buy_candidate"
    BUY_CANDIDATE = "buy_candidate"
    WATCHLIST = "watchlist"
    FAIRLY_VALUED = "fairly_valued"
    EXPENSIVE = "expensive"
    HIGHLY_EXPENSIVE = "highly_expensive"


class OverallQualityFlag(str, Enum):
    """Overall aggregator quality / risk flags."""

    HIGH_CONFIDENCE = "high_confidence"
    LOW_CONFIDENCE = "low_confidence"
    STRONG_CONSENSUS = "strong_consensus"
    WEAK_CONSENSUS = "weak_consensus"
    WIDE_VALUATION_RANGE = "wide_valuation_range"
    NARROW_VALUATION_RANGE = "narrow_valuation_range"
    SPECULATIVE = "speculative"
    INCOMPLETE_DATASET = "incomplete_dataset"


@dataclass(frozen=True, slots=True)
class MosThresholds:
    """Configurable MoS / classification thresholds (fractions of IV)."""

    deep_value: float = 0.40
    undervalued: float = 0.15
    fairly_band: float = 0.10
    overvalued: float = -0.15
    extremely_overvalued: float = -0.40


@dataclass(frozen=True, slots=True)
class MethodSummaryRow:
    """One method's contribution to the overall view."""

    method: str
    intrinsic_value: float | None
    intrinsic_value_per_share: float | None
    confidence: str
    confidence_score: float
    weight: float
    agreement_pct: float | None
    status: str
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConsistencySummary:
    """Cross-method consistency snapshot."""

    agreement_pct: float
    highest_method: str | None
    lowest_method: str | None
    largest_outlier: str | None
    most_trusted_method: str | None
    most_stable_method: str | None


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    """Aggregated scenario anchors."""

    bear: float | None
    base: float | None
    bull: float | None
    custom: Mapping[str, float]
    outcomes: tuple[ScenarioOutcome, ...]


@dataclass(frozen=True, slots=True)
class OverallSensitivitySummary:
    """Aggregated sensitivity highlights."""

    highest_risk_driver: str | None
    most_stable_driver: str | None
    sensitivity_ranking: tuple[str, ...]
    average_sensitivity: float | None
    method_scores: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class OverallInputs:
    """Inputs for Overall Valuation — completed results only.

    Prefer a rich :class:`ConsensusResult`. Alternatively supply a consensus
    :class:`ValuationResult` / V2 payload plus optional method results.
    """

    current_market_price: float
    consensus: ConsensusResult | ValuationResult | Mapping[str, Any]
    methods: Sequence[ValuationResult | Mapping[str, Any]] = ()
    shares_outstanding: float | None = None
    mos_thresholds: MosThresholds = field(default_factory=MosThresholds)
    currency: str = "USD"
    wide_range_pct: float = 0.40
    narrow_range_pct: float = 0.10
    required_method_count: int = 0


@dataclass(frozen=True, slots=True)
class OverallValuationResult:
    """Full Overall Valuation research result (Phase 1 suite aggregator)."""

    version: str
    currency: str
    disclaimer: str
    methodology: str
    overall_intrinsic_value: OverallExplainedValue
    overall_intrinsic_value_per_share: OverallExplainedValue
    current_market_price: OverallExplainedValue
    margin_of_safety: OverallExplainedValue
    premium_discount: OverallExplainedValue
    mos_classification: MosClassification
    research_label: ResearchLabel
    consensus_value: OverallExplainedValue
    consensus_confidence: str
    overall_confidence: str
    confidence_detail: ConfidenceDetail
    overall_valuation_score: OverallExplainedValue
    confidence_interval: tuple[float, float]
    bull_value: float | None
    base_value: float | None
    bear_value: float | None
    fair_value_range: tuple[float, float]
    valuation_range: tuple[float, float]
    method_summary: tuple[MethodSummaryRow, ...]
    method_rankings: tuple[str, ...]
    method_weights: tuple[MethodWeightDetail, ...] | tuple[tuple[str, float], ...]
    method_agreement: float
    consistency_score: float
    consistency: ConsistencySummary
    applicability_summary: Mapping[str, float]
    scenario_summary: ScenarioSummary
    sensitivity_summary: OverallSensitivitySummary
    quality_flags: tuple[OverallQualityFlag, ...]
    core_quality_flags: tuple[QualityFlag, ...]
    validation_summary: ValidationSummary
    explainability: tuple[OverallExplainedValue, ...]
    warnings: tuple[str, ...]
    limitations: tuple[str, ...]
    metadata: ValuationMetadata
    overall_valuation_enabled: bool = True
    execution_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "currency": self.currency,
            "disclaimer": self.disclaimer,
            "methodology": self.methodology,
            "overall_intrinsic_value": self.overall_intrinsic_value.value,
            "overall_intrinsic_value_per_share": self.overall_intrinsic_value_per_share.value,
            "current_market_price": self.current_market_price.value,
            "margin_of_safety": self.margin_of_safety.value,
            "premium_discount": self.premium_discount.value,
            "mos_classification": self.mos_classification.value,
            "research_label": self.research_label.value,
            "consensus_value": self.consensus_value.value,
            "consensus_confidence": self.consensus_confidence,
            "overall_confidence": self.overall_confidence,
            "overall_valuation_score": self.overall_valuation_score.value,
            "confidence_interval": list(self.confidence_interval),
            "bull_value": self.bull_value,
            "base_value": self.base_value,
            "bear_value": self.bear_value,
            "fair_value_range": list(self.fair_value_range),
            "valuation_range": list(self.valuation_range),
            "method_agreement": self.method_agreement,
            "consistency_score": self.consistency_score,
            "quality_flags": [f.value for f in self.quality_flags],
            "overall_valuation_enabled": self.overall_valuation_enabled,
            "execution_time_ms": self.execution_time_ms,
            "warnings": list(self.warnings),
        }


def _empty_sensitivity() -> SensitivityMatrix:
    return SensitivityMatrix(grids={})


def to_valuation_result(result: OverallValuationResult) -> ValuationResult:
    """Map overall result onto shared :class:`ValuationResult`."""
    return ValuationResult(
        model_name="overall",
        version=result.version,
        methodology=result.methodology,
        intrinsic_value=result.overall_intrinsic_value.value,
        enterprise_value=None,
        equity_value=result.overall_intrinsic_value.value,
        intrinsic_value_per_share=result.overall_intrinsic_value_per_share.value,
        margin_of_safety=result.margin_of_safety.value,
        confidence_score=result.confidence_detail.score,
        confidence_level=result.confidence_detail.level,
        quality_flags=result.core_quality_flags,
        sensitivity_results=_empty_sensitivity(),
        scenario_results=result.scenario_summary.outcomes,
        validation_summary=result.validation_summary,
        explainability=result.explainability,
        research_disclaimer=result.disclaimer,
        execution_time_ms=result.execution_time_ms,
        metadata=result.metadata,
        currency=result.currency,
        confidence_explanation=result.confidence_detail.explanation,
    )


def to_v2_aggregate_payload(result: OverallValuationResult) -> dict[str, object]:
    """Stable cite payload for suite / future presentation layers."""
    return {
        "method": "overall",
        "module": "valuation.overall",
        "version": result.version,
        "currency": result.currency,
        "intrinsic_value": result.overall_intrinsic_value.value,
        "intrinsic_value_per_share": result.overall_intrinsic_value_per_share.value,
        "margin_of_safety": result.margin_of_safety.value,
        "mos_classification": result.mos_classification.value,
        "research_label": result.research_label.value,
        "overall_valuation_score": result.overall_valuation_score.value,
        "consistency_score": result.consistency_score,
        "confidence": result.overall_confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "disclaimer": result.disclaimer,
        "core_version": VALUATION_CORE_VERSION,
        "overall_valuation_enabled": True,
        "not_investment_advice": True,
    }
