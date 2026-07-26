"""Public Earnings Quality Intelligence engine (FEATURE-004 Phase 1)."""

from __future__ import annotations

from business_quality import BusinessQualityAnalysis
from financial import FinancialAnalysis

from earnings_quality.exceptions import EarningsQualityValidationError
from earnings_quality.explainability import (
    EARNINGS_QUALITY_RESEARCH_DISCLAIMER,
    aggregate_factors,
    analysis_confidence,
    build_earnings_explainability,
    build_recommendation,
    build_summary,
)
from earnings_quality.metadata import (
    EARNINGS_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    EarningsQualityMetadata,
)
from earnings_quality.models import (
    EarningsQualityAnalysis,
    EarningsQualityExplainability,
    EarningsQualityScore,
    EarningsQualityValidationSummary,
)
from earnings_quality.rules import evaluate_all_components
from earnings_quality.scoring import (
    DEFAULT_EARNINGS_WEIGHTS,
    EarningsQualityWeights,
    earnings_rating_from_score,
    validate_weights,
    weighted_mean,
)
from earnings_quality.validation import validate_framework_inputs

__all__ = ["EarningsQualityEngine"]


class EarningsQualityEngine:
    """Evaluate earnings quality dimensions and compose an explainable assessment.

    Note: This is the FEATURE-004 package façade (``earnings_quality``).
    It is distinct from ``business_quality.EarningsQualityEngine`` (F3.2 module).
    """

    def __init__(self, *, default_weights: EarningsQualityWeights | None = None) -> None:
        self._default_weights = validate_weights(
            default_weights or DEFAULT_EARNINGS_WEIGHTS
        )

    @property
    def version(self) -> str:
        return EARNINGS_QUALITY_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> EarningsQualityWeights:
        return self._default_weights

    def validate(
        self,
        financial_analysis: object | None,
        business_quality_analysis: object | None,
        *,
        metadata: object | None = None,
    ) -> EarningsQualityValidationSummary:
        effective_metadata = metadata if metadata is not None else self._metadata()
        return validate_framework_inputs(
            financial_analysis,
            business_quality_analysis,
            effective_metadata,
        )

    def analyze(
        self,
        financial_analysis: FinancialAnalysis,
        business_quality_analysis: BusinessQualityAnalysis,
        *,
        metadata: EarningsQualityMetadata | None = None,
        weights: EarningsQualityWeights | None = None,
    ) -> EarningsQualityAnalysis:
        effective_metadata = metadata if metadata is not None else self._metadata()
        effective_weights = validate_weights(weights or self._default_weights)
        validation = self.validate(
            financial_analysis,
            business_quality_analysis,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise EarningsQualityValidationError("; ".join(validation.errors))

        components = evaluate_all_components(
            financial_analysis,
            business_quality_analysis,
            effective_weights,
        )
        pairs: list[tuple[float, float]] = []
        for component in components:
            if component.score.value is None:
                continue
            pairs.append((component.score.value, component.weight))
        overall = weighted_mean(pairs)
        rating = earnings_rating_from_score(overall)
        confidence = analysis_confidence(components)
        strengths, weaknesses, risks = aggregate_factors(components)
        explainability = build_earnings_explainability(
            effective_metadata,
            components,
            confidence,
            rating,
            overall,
        )
        evidence = tuple(
            item for component in components for item in component.evidence
        )
        score = (
            EarningsQualityScore(value=None, status="insufficient_data")
            if overall is None
            else EarningsQualityScore(value=round(overall, 4), status="assessed")
        )
        return EarningsQualityAnalysis(
            metadata=effective_metadata,
            validation=validation,
            score=score,
            evidence=evidence,
            confidence=confidence,
            explainability=explainability,
            components=components,
            overall_earnings_rating=rating,
            summary=build_summary(rating, overall, components),
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            recommendation=build_recommendation(rating, confidence),
            weights_used=effective_weights,
            research_disclaimer=EARNINGS_QUALITY_RESEARCH_DISCLAIMER,
        )

    def explain(self, analysis: EarningsQualityAnalysis) -> EarningsQualityExplainability:
        if not isinstance(analysis, EarningsQualityAnalysis):
            raise EarningsQualityValidationError(
                f"Accept ONLY EarningsQualityAnalysis, got {type(analysis).__name__}"
            )
        return analysis.explainability

    def _metadata(self) -> EarningsQualityMetadata:
        return EarningsQualityMetadata(engine_version=self.version)
