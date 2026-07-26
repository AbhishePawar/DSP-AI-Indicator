"""Public Management Quality Intelligence engine (FEATURE-002 Phase 1)."""

from __future__ import annotations

from business_quality import BusinessQualityAnalysis
from financial import FinancialAnalysis

from management_quality.exceptions import ManagementQualityValidationError
from management_quality.explainability import (
    MANAGEMENT_QUALITY_RESEARCH_DISCLAIMER,
    aggregate_factors,
    analysis_confidence,
    build_management_explainability,
    build_recommendation,
    build_summary,
)
from management_quality.metadata import (
    MANAGEMENT_QUALITY_VERSION,
    FRAMEWORK_VERSION,
    ManagementMetadata,
)
from management_quality.models import (
    ManagementAnalysis,
    ManagementExplainability,
    ManagementScore,
    ManagementValidationSummary,
)
from management_quality.rules import evaluate_all_components
from management_quality.scoring import (
    DEFAULT_MANAGEMENT_WEIGHTS,
    ManagementWeights,
    management_rating_from_score,
    validate_weights,
    weighted_mean,
)
from management_quality.validation import validate_framework_inputs

__all__ = ["ManagementEngine"]


class ManagementEngine:
    """Evaluate management quality dimensions and compose an explainable assessment."""

    def __init__(self, *, default_weights: ManagementWeights | None = None) -> None:
        self._default_weights = validate_weights(
            default_weights or DEFAULT_MANAGEMENT_WEIGHTS
        )

    @property
    def version(self) -> str:
        return MANAGEMENT_QUALITY_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> ManagementWeights:
        return self._default_weights

    def validate(
        self,
        financial_analysis: object | None,
        business_quality_analysis: object | None,
        *,
        metadata: object | None = None,
    ) -> ManagementValidationSummary:
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
        metadata: ManagementMetadata | None = None,
        weights: ManagementWeights | None = None,
    ) -> ManagementAnalysis:
        effective_metadata = metadata if metadata is not None else self._metadata()
        effective_weights = validate_weights(weights or self._default_weights)
        validation = self.validate(
            financial_analysis,
            business_quality_analysis,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise ManagementQualityValidationError("; ".join(validation.errors))

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
        rating = management_rating_from_score(overall)
        confidence = analysis_confidence(components)
        strengths, weaknesses, risks = aggregate_factors(components)
        explainability = build_management_explainability(
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
            ManagementScore(value=None, status="insufficient_data")
            if overall is None
            else ManagementScore(value=round(overall, 4), status="assessed")
        )
        return ManagementAnalysis(
            metadata=effective_metadata,
            validation=validation,
            score=score,
            evidence=evidence,
            confidence=confidence,
            explainability=explainability,
            components=components,
            overall_management_rating=rating,
            summary=build_summary(rating, overall, components),
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            recommendation=build_recommendation(rating, confidence),
            weights_used=effective_weights,
            research_disclaimer=MANAGEMENT_QUALITY_RESEARCH_DISCLAIMER,
        )

    def explain(self, analysis: ManagementAnalysis) -> ManagementExplainability:
        if not isinstance(analysis, ManagementAnalysis):
            raise ManagementQualityValidationError(
                f"Accept ONLY ManagementAnalysis, got {type(analysis).__name__}"
            )
        return analysis.explainability

    def _metadata(self) -> ManagementMetadata:
        return ManagementMetadata(engine_version=self.version)
