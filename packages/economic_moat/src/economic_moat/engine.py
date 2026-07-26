"""Public Economic Moat Intelligence engine (FEATURE-001 Phase 1)."""

from __future__ import annotations

from business_quality import BusinessQualityAnalysis
from financial import FinancialAnalysis

from economic_moat.exceptions import EconomicMoatValidationError
from economic_moat.explainability import (
    ECONOMIC_MOAT_RESEARCH_DISCLAIMER,
    aggregate_factors,
    analysis_confidence,
    build_moat_explainability,
    build_recommendation,
    build_summary,
)
from economic_moat.metadata import (
    ECONOMIC_MOAT_VERSION,
    FRAMEWORK_VERSION,
    EconomicMetadata,
)
from economic_moat.models import (
    EconomicAnalysis,
    EconomicExplainability,
    EconomicScore,
    EconomicValidationSummary,
)
from economic_moat.rules import evaluate_all_components
from economic_moat.scoring import (
    DEFAULT_MOAT_WEIGHTS,
    MoatWeights,
    moat_rating_from_score,
    validate_weights,
    weighted_mean,
)
from economic_moat.validation import validate_framework_inputs

__all__ = ["EconomicEngine"]


class EconomicEngine:
    """Evaluate economic moat dimensions and compose an explainable assessment."""

    def __init__(self, *, default_weights: MoatWeights | None = None) -> None:
        self._default_weights = validate_weights(
            default_weights or DEFAULT_MOAT_WEIGHTS
        )

    @property
    def version(self) -> str:
        return ECONOMIC_MOAT_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> MoatWeights:
        return self._default_weights

    def validate(
        self,
        financial_analysis: object | None,
        business_quality_analysis: object | None,
        *,
        metadata: object | None = None,
    ) -> EconomicValidationSummary:
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
        metadata: EconomicMetadata | None = None,
        weights: MoatWeights | None = None,
    ) -> EconomicAnalysis:
        """Run rule-based moat analysis with full evidence trail."""
        effective_metadata = metadata if metadata is not None else self._metadata()
        effective_weights = validate_weights(weights or self._default_weights)
        validation = self.validate(
            financial_analysis,
            business_quality_analysis,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise EconomicMoatValidationError("; ".join(validation.errors))

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
        rating = moat_rating_from_score(overall)
        confidence = analysis_confidence(components)
        positives, negatives, risks = aggregate_factors(components)
        explainability = build_moat_explainability(
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
            EconomicScore(value=None, status="insufficient_data")
            if overall is None
            else EconomicScore(value=round(overall, 4), status="assessed")
        )
        return EconomicAnalysis(
            metadata=effective_metadata,
            validation=validation,
            score=score,
            evidence=evidence,
            confidence=confidence,
            explainability=explainability,
            components=components,
            overall_moat_rating=rating,
            summary=build_summary(rating, overall, components),
            positive_factors=positives,
            negative_factors=negatives,
            risks=risks,
            recommendation=build_recommendation(rating, confidence),
            weights_used=effective_weights,
            research_disclaimer=ECONOMIC_MOAT_RESEARCH_DISCLAIMER,
        )

    def explain(self, analysis: EconomicAnalysis) -> EconomicExplainability:
        if not isinstance(analysis, EconomicAnalysis):
            raise EconomicMoatValidationError(
                f"Accept ONLY EconomicAnalysis, got {type(analysis).__name__}"
            )
        return analysis.explainability

    def _metadata(self) -> EconomicMetadata:
        return EconomicMetadata(engine_version=self.version)
