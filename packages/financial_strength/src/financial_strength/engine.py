"""Public Financial Strength Intelligence engine (FEATURE-003 Phase 1)."""

from __future__ import annotations

from business_quality import BusinessQualityAnalysis
from financial import FinancialAnalysis

from financial_strength.exceptions import FinancialStrengthValidationError
from financial_strength.explainability import (
    FINANCIAL_STRENGTH_RESEARCH_DISCLAIMER,
    aggregate_factors,
    analysis_confidence,
    build_recommendation,
    build_strength_explainability,
    build_summary,
)
from financial_strength.metadata import (
    FINANCIAL_STRENGTH_VERSION,
    FRAMEWORK_VERSION,
    FinancialStrengthMetadata,
)
from financial_strength.models import (
    FinancialStrengthAnalysis,
    FinancialStrengthExplainability,
    FinancialStrengthScore,
    FinancialStrengthValidationSummary,
)
from financial_strength.rules import evaluate_all_components
from financial_strength.scoring import (
    DEFAULT_STRENGTH_WEIGHTS,
    FinancialStrengthWeights,
    strength_rating_from_score,
    validate_weights,
    weighted_mean,
)
from financial_strength.validation import validate_framework_inputs

__all__ = ["FinancialStrengthEngine"]


class FinancialStrengthEngine:
    """Evaluate financial strength dimensions and compose an explainable assessment."""

    def __init__(
        self, *, default_weights: FinancialStrengthWeights | None = None
    ) -> None:
        self._default_weights = validate_weights(
            default_weights or DEFAULT_STRENGTH_WEIGHTS
        )

    @property
    def version(self) -> str:
        return FINANCIAL_STRENGTH_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> FinancialStrengthWeights:
        return self._default_weights

    def validate(
        self,
        financial_analysis: object | None,
        business_quality_analysis: object | None,
        *,
        metadata: object | None = None,
    ) -> FinancialStrengthValidationSummary:
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
        metadata: FinancialStrengthMetadata | None = None,
        weights: FinancialStrengthWeights | None = None,
    ) -> FinancialStrengthAnalysis:
        effective_metadata = metadata if metadata is not None else self._metadata()
        effective_weights = validate_weights(weights or self._default_weights)
        validation = self.validate(
            financial_analysis,
            business_quality_analysis,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise FinancialStrengthValidationError("; ".join(validation.errors))

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
        rating = strength_rating_from_score(overall)
        confidence = analysis_confidence(components)
        strengths, weaknesses, risks, key_metrics = aggregate_factors(components)
        explainability = build_strength_explainability(
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
            FinancialStrengthScore(value=None, status="insufficient_data")
            if overall is None
            else FinancialStrengthScore(value=round(overall, 4), status="assessed")
        )
        return FinancialStrengthAnalysis(
            metadata=effective_metadata,
            validation=validation,
            score=score,
            evidence=evidence,
            confidence=confidence,
            explainability=explainability,
            components=components,
            overall_strength_rating=rating,
            summary=build_summary(rating, overall, components),
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            key_metrics=key_metrics,
            recommendation=build_recommendation(rating, confidence),
            weights_used=effective_weights,
            research_disclaimer=FINANCIAL_STRENGTH_RESEARCH_DISCLAIMER,
        )

    def explain(
        self, analysis: FinancialStrengthAnalysis
    ) -> FinancialStrengthExplainability:
        if not isinstance(analysis, FinancialStrengthAnalysis):
            raise FinancialStrengthValidationError(
                f"Accept ONLY FinancialStrengthAnalysis, got {type(analysis).__name__}"
            )
        return analysis.explainability

    def _metadata(self) -> FinancialStrengthMetadata:
        return FinancialStrengthMetadata(engine_version=self.version)
