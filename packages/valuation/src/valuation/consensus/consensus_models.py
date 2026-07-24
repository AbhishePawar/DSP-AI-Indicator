"""Domain models for Cross-Method Validation & Consensus — research-only.

Accepts standardized :class:`~valuation.core.result_models.ValuationResult`
instances or V2 aggregate payloads. Never invokes valuation engines.
Does **not** enable Overall Valuation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

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
from valuation.consensus.consensus_explainability import ConsensusExplainedValue
from valuation.exceptions import ValuationError

__all__ = [
    "CONSENSUS_VERSION",
    "RESEARCH_DISCLAIMER",
    "ConsensusValidationError",
    "MethodCategory",
    "WeightingMode",
    "ConsensusQualityFlag",
    "CompanyProfile",
    "OutlierThresholds",
    "StandardizedMethodResult",
    "MethodWeightDetail",
    "OutlierReport",
    "DisagreementAnalysis",
    "SensitivitySummary",
    "ConsensusInputs",
    "ConsensusResult",
    "normalize_method_input",
    "default_category_for_method",
    "to_valuation_result",
    "to_v2_aggregate_payload",
]

CONSENSUS_VERSION = "0.11.0-consensus"


class ConsensusValidationError(ValuationError):
    """Raised when consensus inputs fail hard validation."""


class MethodCategory(str, Enum):
    """High-level method family for applicability / research weights."""

    INTRINSIC = "intrinsic"
    RELATIVE = "relative"
    ASSET = "asset"
    INCOME = "income"
    DIVIDEND = "dividend"
    RESIDUAL = "residual"
    MARKET = "market"


class WeightingMode(str, Enum):
    """How method weights are derived (must total 100% after normalize)."""

    AUTOMATIC = "automatic"
    MANUAL = "manual"
    EQUAL = "equal"
    CONFIDENCE = "confidence"
    APPLICABILITY = "applicability"
    RESEARCH = "research"


class ConsensusQualityFlag(str, Enum):
    """Consensus agreement / risk flags."""

    HIGH_AGREEMENT = "high_agreement"
    MEDIUM_AGREEMENT = "medium_agreement"
    LOW_AGREEMENT = "low_agreement"
    OUTLIER_PRESENT = "outlier_present"
    WEAK_DATASET = "weak_dataset"
    STRONG_CONSENSUS = "strong_consensus"
    SPECULATIVE_CONSENSUS = "speculative_consensus"
    CONFLICTING_METHODS = "conflicting_methods"


# Known method → category; unknown future methods default via heuristic.
_KNOWN_CATEGORIES: dict[str, MethodCategory] = {
    "dcf": MethodCategory.INTRINSIC,
    "discounted_cash_flow": MethodCategory.INTRINSIC,
    "reverse_dcf": MethodCategory.MARKET,
    "residual_income": MethodCategory.RESIDUAL,
    "epv": MethodCategory.INCOME,
    "graham": MethodCategory.INTRINSIC,
    "ddm": MethodCategory.DIVIDEND,
    "asset_based": MethodCategory.ASSET,
    "relative": MethodCategory.RELATIVE,
}


def default_category_for_method(method: str) -> MethodCategory:
    """Map a method name to a category; unknown methods stay plug-in friendly."""
    key = method.strip().lower().replace("-", "_").replace(" ", "_")
    if key in _KNOWN_CATEGORIES:
        return _KNOWN_CATEGORIES[key]
    if "relative" in key or "multiple" in key or key in {"pe", "pb", "ev_ebitda"}:
        return MethodCategory.RELATIVE
    if "asset" in key or "nav" in key or "liquidation" in key:
        return MethodCategory.ASSET
    if "dividend" in key or "ddm" in key:
        return MethodCategory.DIVIDEND
    if "residual" in key or "riv" in key:
        return MethodCategory.RESIDUAL
    if "reverse" in key or "implied" in key:
        return MethodCategory.MARKET
    if "epv" in key or "earnings" in key:
        return MethodCategory.INCOME
    return MethodCategory.INTRINSIC


@dataclass(frozen=True, slots=True)
class CompanyProfile:
    """Optional company characteristics for applicability scoring."""

    pays_dividend: bool = False
    asset_heavy: bool = False
    growth_company: bool = False
    loss_making: bool = False
    financial_institution: bool = False
    holding_company: bool = False


@dataclass(frozen=True, slots=True)
class OutlierThresholds:
    """Configurable outlier detection thresholds."""

    z_score: float = 2.5
    iqr_multiplier: float = 1.5
    median_deviation_pct: float = 0.50
    extreme_ratio: float = 5.0
    exclude_outliers_from_consensus: bool = True


@dataclass(frozen=True, slots=True)
class StandardizedMethodResult:
    """Normalized view of one method contribution."""

    method: str
    category: MethodCategory
    intrinsic_value: float | None
    intrinsic_value_per_share: float | None
    confidence_score: float
    confidence_level: str
    quality_flags: tuple[str, ...]
    scenario_results: tuple[ScenarioOutcome, ...]
    sensitivity_results: SensitivityMatrix | None
    validation_ok: bool
    validation_warnings: tuple[str, ...]
    methodology: str
    version: str
    currency: str
    explainability_notes: tuple[str, ...] = ()
    source: str = "valuation_result"  # or "v2_payload"


@dataclass(frozen=True, slots=True)
class MethodWeightDetail:
    """Weight + applicability breakdown for one method."""

    method: str
    category: MethodCategory
    weight: float
    applicability_score: float
    confidence_score: float
    included_in_consensus: bool
    is_outlier: bool
    explanation: str


@dataclass(frozen=True, slots=True)
class OutlierReport:
    """Outlier detection summary for one method."""

    method: str
    value: float
    z_score: float | None
    iqr_flag: bool
    median_deviation: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DisagreementAnalysis:
    """Why methods diverge (research narrative)."""

    overall_spread_pct: float
    pairwise_max_pct: float
    notes: tuple[str, ...]
    method_notes: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class SensitivitySummary:
    """Cross-method sensitivity aggregation."""

    highest_sensitivity: float | None
    lowest_sensitivity: float | None
    average_sensitivity: float | None
    most_stable_method: str | None
    least_stable_method: str | None
    method_scores: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class ConsensusInputs:
    """Inputs for consensus — standardized results only (no engine calls).

    Provide ``methods`` as :class:`ValuationResult` and/or V2 aggregate
    payload dicts. Optional ``manual_weights`` keyed by method name.
    """

    methods: Sequence[ValuationResult | Mapping[str, Any]]
    weighting_mode: WeightingMode = WeightingMode.AUTOMATIC
    company_profile: CompanyProfile = field(default_factory=CompanyProfile)
    manual_weights: Mapping[str, float] = field(default_factory=dict)
    outlier_thresholds: OutlierThresholds = field(default_factory=OutlierThresholds)
    trim_fraction: float = 0.10
    current_market_price: float | None = None
    shares_outstanding: float | None = None
    currency: str = "USD"
    category_overrides: Mapping[str, MethodCategory] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ConsensusResult:
    """Full cross-method consensus research result."""

    version: str
    currency: str
    disclaimer: str
    methodology: str
    consensus_intrinsic_value: ConsensusExplainedValue
    consensus_per_share: ConsensusExplainedValue
    consensus_confidence: str
    confidence_detail: ConfidenceDetail
    weighted_mean: ConsensusExplainedValue
    weighted_median: ConsensusExplainedValue
    median: ConsensusExplainedValue
    trimmed_mean: ConsensusExplainedValue
    method_rankings: tuple[str, ...]
    method_weights: tuple[MethodWeightDetail, ...]
    applicability_scores: Mapping[str, float]
    outliers: tuple[OutlierReport, ...]
    disagreement: DisagreementAnalysis
    consistency_score: ConsensusExplainedValue
    confidence_interval: tuple[float, float]
    upper_range: float
    lower_range: float
    scenario_results: tuple[ScenarioOutcome, ...]
    sensitivity_summary: SensitivitySummary
    quality_flags: tuple[ConsensusQualityFlag, ...]
    core_quality_flags: tuple[QualityFlag, ...]
    validation_summary: ValidationSummary
    explainability: tuple[ConsensusExplainedValue, ...]
    limitations: tuple[str, ...]
    metadata: ValuationMetadata
    standardized_methods: tuple[StandardizedMethodResult, ...]
    execution_time_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "currency": self.currency,
            "disclaimer": self.disclaimer,
            "methodology": self.methodology,
            "consensus_intrinsic_value": self.consensus_intrinsic_value.value,
            "consensus_per_share": self.consensus_per_share.value,
            "consensus_confidence": self.consensus_confidence,
            "weighted_mean": self.weighted_mean.value,
            "weighted_median": self.weighted_median.value,
            "median": self.median.value,
            "trimmed_mean": self.trimmed_mean.value,
            "consistency_score": self.consistency_score.value,
            "confidence_interval": list(self.confidence_interval),
            "upper_range": self.upper_range,
            "lower_range": self.lower_range,
            "quality_flags": [f.value for f in self.quality_flags],
            "method_rankings": list(self.method_rankings),
            "execution_time_ms": self.execution_time_ms,
        }


def _empty_sensitivity() -> SensitivityMatrix:
    return SensitivityMatrix(grids={})


def normalize_method_input(
    item: ValuationResult | Mapping[str, Any],
    *,
    category_overrides: Mapping[str, MethodCategory] | None = None,
) -> StandardizedMethodResult:
    """Normalize a ValuationResult or V2 payload into a standard contribution."""
    overrides = category_overrides or {}
    if isinstance(item, ValuationResult):
        method = item.model_name
        category = overrides.get(method, default_category_for_method(method))
        conf = float(item.confidence_score)
        level = str(item.confidence_level)
        if conf < 0 or (conf != conf) or conf == float("inf"):
            raise ConsensusValidationError(f"invalid confidence for {method}: {conf}")
        return StandardizedMethodResult(
            method=method,
            category=category,
            intrinsic_value=item.intrinsic_value,
            intrinsic_value_per_share=item.intrinsic_value_per_share,
            confidence_score=conf,
            confidence_level=level,
            quality_flags=tuple(f.value for f in item.quality_flags),
            scenario_results=tuple(item.scenario_results),
            sensitivity_results=item.sensitivity_results,
            validation_ok=item.validation_summary.ok,
            validation_warnings=tuple(item.validation_summary.warnings),
            methodology=item.methodology,
            version=item.version,
            currency=item.currency,
            explainability_notes=tuple(
                e.notes for e in item.explainability if e.notes
            ),
            source="valuation_result",
        )

    if not isinstance(item, Mapping):
        raise ConsensusValidationError(
            f"unsupported method input type: {type(item)!r}"
        )

    method = str(item.get("method") or item.get("model_name") or "").strip()
    if not method:
        raise ConsensusValidationError("v2 payload missing method")
    category = overrides.get(method, default_category_for_method(method))

    iv = item.get("intrinsic_value")
    ivps = item.get("intrinsic_value_per_share")
    if iv is None and item.get("equity_value") is not None:
        iv = item.get("equity_value")

    conf_raw = item.get("confidence_score")
    if conf_raw is None:
        # Map level-only payloads to a mid-band numeric score
        level = str(item.get("confidence") or "medium").lower()
        conf_raw = {"high": 6.0, "medium": 4.0, "low": 2.0}.get(level, 4.0)
    conf = float(conf_raw)
    if conf != conf or conf == float("inf") or conf < 0:
        raise ConsensusValidationError(f"invalid confidence for {method}: {conf}")

    level = str(item.get("confidence") or item.get("confidence_level") or "medium")
    flags_raw = item.get("quality_flags") or ()
    flags = tuple(str(f) for f in flags_raw)

    return StandardizedMethodResult(
        method=method,
        category=category,
        intrinsic_value=float(iv) if iv is not None else None,
        intrinsic_value_per_share=float(ivps) if ivps is not None else None,
        confidence_score=conf,
        confidence_level=level,
        quality_flags=flags,
        scenario_results=(),
        sensitivity_results=None,
        validation_ok=True,
        validation_warnings=(),
        methodology=str(item.get("methodology") or f"{method} (payload)"),
        version=str(item.get("version") or "unknown"),
        currency=str(item.get("currency") or "USD"),
        explainability_notes=(),
        source="v2_payload",
    )


def to_valuation_result(result: ConsensusResult) -> ValuationResult:
    """Map consensus onto shared :class:`ValuationResult`."""
    return ValuationResult(
        model_name="consensus",
        version=result.version,
        methodology=result.methodology,
        intrinsic_value=result.consensus_intrinsic_value.value,
        enterprise_value=None,
        equity_value=result.consensus_intrinsic_value.value,
        intrinsic_value_per_share=result.consensus_per_share.value,
        margin_of_safety=None,
        confidence_score=result.confidence_detail.score,
        confidence_level=result.confidence_detail.level,
        quality_flags=result.core_quality_flags,
        sensitivity_results=_empty_sensitivity(),
        scenario_results=result.scenario_results,
        validation_summary=result.validation_summary,
        explainability=result.explainability,
        research_disclaimer=result.disclaimer,
        execution_time_ms=result.execution_time_ms,
        metadata=result.metadata,
        currency=result.currency,
        confidence_explanation=result.confidence_detail.explanation,
    )


def to_v2_aggregate_payload(result: ConsensusResult) -> dict[str, object]:
    """Stable cite payload for future V2.0 Overall Valuation Aggregator."""
    return {
        "method": "consensus",
        "module": "valuation.consensus",
        "version": result.version,
        "currency": result.currency,
        "intrinsic_value": result.consensus_intrinsic_value.value,
        "intrinsic_value_per_share": result.consensus_per_share.value,
        "consistency_score": result.consistency_score.value,
        "confidence": result.consensus_confidence,
        "quality_flags": [f.value for f in result.quality_flags],
        "disclaimer": result.disclaimer,
        "core_version": VALUATION_CORE_VERSION,
        "overall_valuation_enabled": False,
    }
