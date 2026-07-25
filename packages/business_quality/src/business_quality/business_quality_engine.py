"""Canonical Business Quality Engine — F3.6 orchestration.

Composes EQ / CA / BC / CP once each. No new financial calculations.
"""

from __future__ import annotations

from typing import Any

from business_quality.business_characteristics_engine import (
    BusinessCharacteristicsEngine,
)
from business_quality.business_characteristics_models import (
    BusinessCharacteristicsAnalysis,
)
from business_quality.business_quality_explainability import (
    BUSINESS_QUALITY_ENGINE_DISCLAIMER,
    bq_explanation,
    merge_module_explainability,
)
from business_quality.business_quality_models import (
    DEFAULT_BUSINESS_QUALITY_WEIGHTS,
    AggregatedFlag,
    AggregatedFlags,
    BusinessQualityAnalysis,
    BusinessQualityFlag,
    BusinessQualityScore,
    BusinessQualitySummary,
    BusinessQualityWeights,
    FlagSeverity,
    OverallAssessment,
    OverallRating,
)
from business_quality.business_quality_validation import (
    validate_business_quality_input,
    validate_module_outputs,
    validate_weights,
)
from business_quality.capital_allocation_engine import CapitalAllocationEngine
from business_quality.capital_allocation_models import CapitalAllocationAnalysis
from business_quality.competitive_position_engine import CompetitivePositionEngine
from business_quality.competitive_position_models import CompetitivePositionAnalysis
from business_quality.earnings_quality_engine import (
    EarningsQualityEngine,
    _aggregate_confidence,
    _rating_from_01,
)
from business_quality.earnings_quality_models import EarningsQualityAnalysis
from business_quality.explainability import RESEARCH_DISCLAIMER
from business_quality.metadata import (
    BUSINESS_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    BusinessQualityMetadata,
)
from business_quality.scoring import Confidence, Rating, Score, weighted_mean
from business_quality.validation import (
    empty_validation,
    merge_validation_results,
)

__all__ = [
    "BUSINESS_QUALITY_ENGINE_VERSION",
    "BusinessQualityEngine",
    "aggregate_flags",
    "compose_overall_score",
    "overall_rating_from_01",
]

BUSINESS_QUALITY_ENGINE_VERSION = "0.6.0-business-quality-engine"

_POSITIVE_FLAGS: dict[str, frozenset[str]] = {
    "earnings_quality": frozenset(
        {
            "high_earnings_quality",
            "cash_supported_earnings",
            "recurring_earnings",
            "stable_margins",
        }
    ),
    "capital_allocation": frozenset(
        {
            "excellent_capital_allocation",
            "disciplined_reinvestment",
            "shareholder_friendly",
            "healthy_cash_deployment",
        }
    ),
    "business_characteristics": frozenset(
        {
            "asset_light",
            "highly_scalable",
            "operationally_stable",
            "resilient_business",
            "strong_cash_generator",
            "margin_durable",
        }
    ),
    "competitive_position": frozenset(
        {
            "strong_pricing_power",
            "durable_margins",
            "high_capital_efficiency",
            "operational_excellence",
            "strong_competitive_position",
        }
    ),
}

_CRITICAL_FLAGS: dict[str, frozenset[str]] = {
    "earnings_quality": frozenset(
        {
            "aggressive_accounting_risk",
            "high_accrual_risk",
        }
    ),
    "capital_allocation": frozenset(
        {
            "weak_capital_allocation",
            "debt_dependent",
        }
    ),
    "business_characteristics": frozenset(),
    "competitive_position": frozenset(
        {
            "weak_competitive_position",
            "declining_profitability",
        }
    ),
}

_WARNING_FLAGS: dict[str, frozenset[str]] = {
    "earnings_quality": frozenset(
        {
            "weak_cash_support",
            "volatile_earnings",
        }
    ),
    "capital_allocation": frozenset(
        {
            "excessive_capital_spending",
            "dividend_at_risk",
            "inconsistent_allocation",
        }
    ),
    "business_characteristics": frozenset(
        {
            "capital_intensive",
            "cyclical_business",
        }
    ),
    "competitive_position": frozenset(
        {
            "margin_pressure",
            "weak_capital_efficiency",
        }
    ),
}

_SEVERITY_ORDER = {
    FlagSeverity.CRITICAL: 0,
    FlagSeverity.WARNING: 1,
    FlagSeverity.POSITIVE: 2,
}


class BusinessQualityEngine:
    """Canonical public entry for Business Quality Intelligence (F3.6)."""

    def __init__(
        self,
        *,
        default_weights: BusinessQualityWeights | None = None,
    ) -> None:
        self._version = BUSINESS_QUALITY_VERSION
        self._engine_version = BUSINESS_QUALITY_ENGINE_VERSION
        self._default_weights = validate_weights(
            default_weights or DEFAULT_BUSINESS_QUALITY_WEIGHTS
        )
        self._earnings = EarningsQualityEngine()
        self._capital = CapitalAllocationEngine()
        self._characteristics = BusinessCharacteristicsEngine()
        self._competitive = CompetitivePositionEngine()

    @property
    def version(self) -> str:
        return self._version

    @property
    def engine_version(self) -> str:
        return self._engine_version

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> BusinessQualityWeights:
        return self._default_weights

    def create_shell_analysis(
        self,
        *,
        company: str = "",
        ticker: str = "",
    ) -> BusinessQualityAnalysis:
        """Return an empty immutable analysis shell (framework placeholder)."""
        return BusinessQualityAnalysis(
            metadata=BusinessQualityMetadata(
                engine_version=self._version,
                framework_version=FRAMEWORK_VERSION,
                company=company,
                ticker=ticker,
                modules_composed=("business_quality_framework",),
            ),
            validation=empty_validation(ok=True),
            score=None,
            summary=BusinessQualitySummary(
                headline="Business Quality Framework shell (no full suite yet)",
            ),
            quality_flags=(),
            explainability=(),
            research_disclaimer=RESEARCH_DISCLAIMER,
        )

    def analyze_earnings_quality(
        self, financial_analysis: Any
    ) -> EarningsQualityAnalysis:
        """Run Earnings Quality Intelligence (F3.2)."""
        return self._earnings.analyze(financial_analysis)

    def analyze_capital_allocation(
        self, financial_analysis: Any
    ) -> CapitalAllocationAnalysis:
        """Run Capital Allocation Intelligence (F3.3)."""
        return self._capital.analyze(financial_analysis)

    def analyze_business_characteristics(
        self, financial_analysis: Any
    ) -> BusinessCharacteristicsAnalysis:
        """Run Business Characteristics Intelligence (F3.4)."""
        return self._characteristics.analyze(financial_analysis)

    def analyze_competitive_position(
        self, financial_analysis: Any
    ) -> CompetitivePositionAnalysis:
        """Run Competitive Position Indicators (F3.5)."""
        return self._competitive.analyze(financial_analysis)

    def analyze(
        self,
        financial_analysis: Any,
        *,
        weights: BusinessQualityWeights | None = None,
    ) -> BusinessQualityAnalysis:
        """Compose EQ + CA + BC + CP into a single BusinessQualityAnalysis.

        Each intelligence module executes exactly once.
        """
        input_validation = validate_business_quality_input(financial_analysis)
        weights_used = validate_weights(weights or self._default_weights)

        eq = self.analyze_earnings_quality(financial_analysis)
        ca = self.analyze_capital_allocation(financial_analysis)
        bc = self.analyze_business_characteristics(financial_analysis)
        cp = self.analyze_competitive_position(financial_analysis)

        module_validation = validate_module_outputs(
            earnings_quality=eq,
            capital_allocation=ca,
            business_characteristics=bc,
            competitive_position=cp,
        )

        overall_01, weighted_parts = compose_overall_score(
            eq=eq, ca=ca, bc=bc, cp=cp, weights=weights_used
        )
        overall_score = Score(
            value=None if overall_01 is None else overall_01 * 100.0
        )
        overall_rating = overall_rating_from_01(overall_01)
        legacy_rating = _rating_from_01(overall_01)
        confidence = _aggregate_confidence(
            [eq.confidence, ca.confidence, bc.confidence, cp.confidence]
        )
        bq_flag = _map_overall_to_bq_flag(overall_rating, legacy_rating)
        overall_flags = aggregate_flags(eq=eq, ca=ca, bc=bc, cp=cp)

        assessments = (
            tuple(eq.assessments)
            + tuple(ca.assessments)
            + tuple(bc.assessments)
            + tuple(cp.assessments)
        )
        validation = merge_validation_results(
            [
                input_validation,
                module_validation,
                eq.validation,
                ca.validation,
                bc.validation,
                cp.validation,
            ]
        )
        strengths = _strengths(eq, ca, bc, cp)
        weaknesses = _weaknesses(eq, ca, bc, cp)
        evidence_summary = tuple(
            dict.fromkeys(
                list(eq.evidence[:2])
                + list(ca.evidence[:2])
                + list(bc.evidence[:2])
                + list(cp.evidence[:2])
            )
        )
        limitations = (
            "Overall score uses configurable module weights only; no statement math.",
            "No peer comparison, industry datasets, valuation, or forecasting.",
            "Module confidence and coverage limit overall confidence.",
        )
        module_refs = (
            "FinancialAnalysis → EarningsQualityAnalysis",
            "FinancialAnalysis → CapitalAllocationAnalysis",
            "FinancialAnalysis → BusinessCharacteristicsAnalysis",
            "FinancialAnalysis → CompetitivePositionAnalysis",
        )
        reasoning = (
            f"Weighted composition "
            f"(EQ={weights_used.earnings_quality}, "
            f"CA={weights_used.capital_allocation}, "
            f"BC={weights_used.business_characteristics}, "
            f"CP={weights_used.competitive_position}); "
            f"overall={None if overall_01 is None else round(overall_01, 4)}; "
            f"parts={weighted_parts}."
        )
        overall_assessment = OverallAssessment(
            headline=(
                f"Business quality: {overall_rating.value} "
                f"(EQ={eq.overall_rating.value}, CA={ca.overall_rating.value}, "
                f"BC={bc.overall_rating.value}, CP={cp.overall_rating.value})"
            ),
            strengths=strengths,
            weaknesses=weaknesses,
            limitations=limitations,
            evidence_summary=evidence_summary,
            module_references=module_refs,
            reasoning=reasoning,
        )
        overall_explain = bq_explanation(
            title="Overall Business Quality",
            description="Weighted composition of EQ, CA, BC, and CP module scores.",
            evidence=evidence_summary,
            reasoning=reasoning,
            confidence=confidence,
            limitations="; ".join(limitations),
            references=module_refs,
        )
        explainability = merge_module_explainability(
            tuple(eq.explainability),
            tuple(ca.explainability),
            tuple(bc.explainability),
            tuple(cp.explainability),
            overall=overall_explain,
        )

        meta = getattr(financial_analysis, "metadata", None)
        return BusinessQualityAnalysis(
            metadata=BusinessQualityMetadata(
                engine_version=self._version,
                framework_version=FRAMEWORK_VERSION,
                company=str(
                    eq.metadata.company
                    or ca.metadata.company
                    or bc.metadata.company
                    or cp.metadata.company
                    or getattr(meta, "company", "")
                    or ""
                ),
                ticker=str(
                    eq.metadata.ticker
                    or ca.metadata.ticker
                    or bc.metadata.ticker
                    or cp.metadata.ticker
                    or getattr(meta, "ticker", "")
                    or ""
                ),
                modules_composed=(
                    "business_quality_framework",
                    "business_quality_engine",
                    "earnings_quality_intelligence",
                    "capital_allocation_intelligence",
                    "business_characteristics_intelligence",
                    "competitive_position_indicators",
                ),
            ),
            validation=validation,
            score=BusinessQualityScore(
                overall=overall_score,
                rating=legacy_rating,
                confidence=confidence,
                assessments=assessments,
            ),
            summary=BusinessQualitySummary(
                headline=overall_assessment.headline,
                strengths=strengths,
                weaknesses=weaknesses,
                key_observations=evidence_summary,
                flag=bq_flag,
            ),
            quality_flags=(bq_flag,),
            explainability=explainability,
            research_disclaimer=(
                f"{BUSINESS_QUALITY_ENGINE_DISCLAIMER} "
                f"{eq.research_disclaimer} {ca.research_disclaimer} "
                f"{bc.research_disclaimer} {cp.research_disclaimer}"
            ),
            overall_score=overall_score,
            overall_rating=overall_rating,
            overall_confidence=confidence,
            overall_assessment=overall_assessment,
            overall_flags=overall_flags,
            earnings_quality=eq,
            capital_allocation=ca,
            business_characteristics=bc,
            competitive_position=cp,
            weights_used=weights_used,
        )


def compose_overall_score(
    *,
    eq: EarningsQualityAnalysis,
    ca: CapitalAllocationAnalysis,
    bc: BusinessCharacteristicsAnalysis,
    cp: CompetitivePositionAnalysis,
    weights: BusinessQualityWeights,
) -> tuple[float | None, dict[str, float | None]]:
    """Compute overall 0–1 score from existing module scores and weights."""
    module_scores = {
        "earnings_quality": _module_01(eq),
        "capital_allocation": _module_01(ca),
        "business_characteristics": _module_01(bc),
        "competitive_position": _module_01(cp),
    }
    weight_map = weights.as_dict()
    parts: list[tuple[float, float]] = []
    for name, value in module_scores.items():
        if value is None:
            continue
        parts.append((value, float(weight_map[name])))
    return weighted_mean(parts), module_scores


def overall_rating_from_01(value: float | None) -> OverallRating:
    """Map a 0–1 score to F3.6 overall ratings including Good."""
    if value is None:
        return OverallRating.AVERAGE
    if value >= 0.85:
        return OverallRating.EXCELLENT
    if value >= 0.75:
        return OverallRating.STRONG
    if value >= 0.65:
        return OverallRating.GOOD
    if value >= 0.50:
        return OverallRating.AVERAGE
    if value >= 0.35:
        return OverallRating.WEAK
    return OverallRating.POOR


def aggregate_flags(
    *,
    eq: EarningsQualityAnalysis,
    ca: CapitalAllocationAnalysis,
    bc: BusinessCharacteristicsAnalysis,
    cp: CompetitivePositionAnalysis,
) -> AggregatedFlags:
    """Merge, deduplicate, and severity-sort module quality flags."""
    collected: list[AggregatedFlag] = []
    seen: set[tuple[str, str]] = set()
    for source, analysis in (
        ("earnings_quality", eq),
        ("capital_allocation", ca),
        ("business_characteristics", bc),
        ("competitive_position", cp),
    ):
        for flag in analysis.quality_flags:
            value = getattr(flag, "value", str(flag))
            key = (source, value)
            if key in seen:
                continue
            seen.add(key)
            severity = _classify_flag(source, value)
            collected.append(
                AggregatedFlag(
                    name=value,
                    source=source,
                    severity=severity,
                    value=value,
                )
            )

    collected.sort(key=lambda f: (_SEVERITY_ORDER[f.severity], f.source, f.value))
    critical = tuple(f for f in collected if f.severity is FlagSeverity.CRITICAL)
    warning = tuple(f for f in collected if f.severity is FlagSeverity.WARNING)
    positive = tuple(f for f in collected if f.severity is FlagSeverity.POSITIVE)
    return AggregatedFlags(
        critical=critical,
        warning=warning,
        positive=positive,
        all_sorted=tuple(collected),
    )


def _module_01(analysis: Any) -> float | None:
    score = getattr(analysis, "overall_score", None)
    if score is None or getattr(score, "value", None) is None:
        return None
    return float(score.value) / 100.0


def _classify_flag(source: str, value: str) -> FlagSeverity:
    if value in _CRITICAL_FLAGS.get(source, frozenset()):
        return FlagSeverity.CRITICAL
    if value in _POSITIVE_FLAGS.get(source, frozenset()):
        return FlagSeverity.POSITIVE
    if value in _WARNING_FLAGS.get(source, frozenset()):
        return FlagSeverity.WARNING
    # Unknown module flags default to warning (research caution)
    return FlagSeverity.WARNING


def _map_overall_to_bq_flag(
    overall: OverallRating, legacy: Rating
) -> BusinessQualityFlag:
    mapping = {
        OverallRating.EXCELLENT: BusinessQualityFlag.EXCELLENT,
        OverallRating.STRONG: BusinessQualityFlag.STRONG,
        OverallRating.GOOD: BusinessQualityFlag.GOOD,
        OverallRating.AVERAGE: BusinessQualityFlag.AVERAGE,
        OverallRating.WEAK: BusinessQualityFlag.WEAK,
        OverallRating.POOR: BusinessQualityFlag.POOR,
    }
    if overall in mapping:
        return mapping[overall]
    legacy_map = {
        Rating.EXCELLENT: BusinessQualityFlag.EXCELLENT,
        Rating.STRONG: BusinessQualityFlag.STRONG,
        Rating.AVERAGE: BusinessQualityFlag.AVERAGE,
        Rating.WEAK: BusinessQualityFlag.WEAK,
        Rating.POOR: BusinessQualityFlag.POOR,
        Rating.UNKNOWN: BusinessQualityFlag.UNKNOWN,
        Rating.INSUFFICIENT_DATA: BusinessQualityFlag.INSUFFICIENT_DATA,
    }
    return legacy_map.get(legacy, BusinessQualityFlag.UNKNOWN)


def _strengths(
    eq: EarningsQualityAnalysis,
    ca: CapitalAllocationAnalysis,
    bc: BusinessCharacteristicsAnalysis,
    cp: CompetitivePositionAnalysis,
) -> tuple[str, ...]:
    out: list[str] = []
    for f in eq.quality_flags:
        if f.value in _POSITIVE_FLAGS["earnings_quality"]:
            out.append(f"Earnings quality flag: {f.value}")
    for f in ca.quality_flags:
        if f.value in _POSITIVE_FLAGS["capital_allocation"]:
            out.append(f"Capital allocation flag: {f.value}")
    for f in bc.quality_flags:
        if f.value in _POSITIVE_FLAGS["business_characteristics"]:
            out.append(f"Business characteristics flag: {f.value}")
    for f in cp.quality_flags:
        if f.value in _POSITIVE_FLAGS["competitive_position"]:
            out.append(f"Competitive position flag: {f.value}")
    return tuple(out)


def _weaknesses(
    eq: EarningsQualityAnalysis,
    ca: CapitalAllocationAnalysis,
    bc: BusinessCharacteristicsAnalysis,
    cp: CompetitivePositionAnalysis,
) -> tuple[str, ...]:
    out: list[str] = []
    for f in eq.quality_flags:
        if f.value in (
            _CRITICAL_FLAGS["earnings_quality"] | _WARNING_FLAGS["earnings_quality"]
        ):
            out.append(f"Earnings quality flag: {f.value}")
    for f in ca.quality_flags:
        if f.value in (
            _CRITICAL_FLAGS["capital_allocation"]
            | _WARNING_FLAGS["capital_allocation"]
        ):
            out.append(f"Capital allocation flag: {f.value}")
    for f in bc.quality_flags:
        if f.value in (
            _CRITICAL_FLAGS["business_characteristics"]
            | _WARNING_FLAGS["business_characteristics"]
        ):
            out.append(f"Business characteristics flag: {f.value}")
    for f in cp.quality_flags:
        if f.value in (
            _CRITICAL_FLAGS["competitive_position"]
            | _WARNING_FLAGS["competitive_position"]
        ):
            out.append(f"Competitive position flag: {f.value}")
    return tuple(out)
