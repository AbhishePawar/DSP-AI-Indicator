"""Public Growth Quality Intelligence engine (FEATURE-005 Phase 1)."""

from __future__ import annotations

from business_quality import BusinessQualityAnalysis
from financial import FinancialAnalysis

from growth_quality.exceptions import GrowthQualityValidationError
from growth_quality.explainability import (
    GROWTH_QUALITY_RESEARCH_DISCLAIMER,
    aggregate_factors,
    analysis_confidence,
    build_growth_explainability,
    build_recommendation,
    build_summary,
)
from growth_quality.metadata import (
    GROWTH_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    GrowthQualityMetadata,
)
from growth_quality.models import (
    GrowthQualityAnalysis,
    GrowthQualityExplainability,
    GrowthQualityScore,
    GrowthQualityValidationSummary,
)
from growth_quality.rules import evaluate_all_components
from growth_quality.scoring import (
    DEFAULT_GROWTH_WEIGHTS,
    GrowthQualityWeights,
    growth_rating_from_score,
    validate_weights,
    weighted_mean,
)
from growth_quality.validation import validate_framework_inputs

__all__ = ["GrowthQualityEngine"]


class GrowthQualityEngine:
    """Evaluate growth quality dimensions and compose an explainable assessment."""

    def __init__(self, *, default_weights: GrowthQualityWeights | None = None) -> None:
        self._default_weights = validate_weights(
            default_weights or DEFAULT_GROWTH_WEIGHTS
        )

    @property
    def version(self) -> str:
        return GROWTH_QUALITY_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> GrowthQualityWeights:
        return self._default_weights

    def validate(
        self,
        financial_analysis: object | None,
        business_quality_analysis: object | None,
        *,
        metadata: object | None = None,
    ) -> GrowthQualityValidationSummary:
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
        metadata: GrowthQualityMetadata | None = None,
        weights: GrowthQualityWeights | None = None,
    ) -> GrowthQualityAnalysis:
        effective_metadata = metadata if metadata is not None else self._metadata()
        effective_weights = validate_weights(weights or self._default_weights)
        validation = self.validate(
            financial_analysis,
            business_quality_analysis,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise GrowthQualityValidationError("; ".join(validation.errors))

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
        rating = growth_rating_from_score(overall)
        confidence = analysis_confidence(components)
        strengths, weaknesses, risks = aggregate_factors(components)
        explainability = build_growth_explainability(
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
            GrowthQualityScore(value=None, status="insufficient_data")
            if overall is None
            else GrowthQualityScore(value=round(overall, 4), status="assessed")
        )
        return GrowthQualityAnalysis(
            metadata=effective_metadata,
            validation=validation,
            score=score,
            evidence=evidence,
            confidence=confidence,
            explainability=explainability,
            components=components,
            overall_growth_rating=rating,
            summary=build_summary(rating, overall, components),
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            recommendation=build_recommendation(rating, confidence),
            weights_used=effective_weights,
            research_disclaimer=GROWTH_QUALITY_RESEARCH_DISCLAIMER,
        )

    def explain(self, analysis: GrowthQualityAnalysis) -> GrowthQualityExplainability:
        if not isinstance(analysis, GrowthQualityAnalysis):
            raise GrowthQualityValidationError(
                f"Accept ONLY GrowthQualityAnalysis, got {type(analysis).__name__}"
            )
        return analysis.explainability

    def _metadata(self) -> GrowthQualityMetadata:
        return GrowthQualityMetadata(engine_version=self.version)
