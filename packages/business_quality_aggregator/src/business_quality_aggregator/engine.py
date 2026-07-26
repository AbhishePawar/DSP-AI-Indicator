"""Public Business Quality Aggregator engine (FEATURE-006 Phase 1).

Distinct from F3.7 ``business_quality.BusinessQualityAggregator``.
"""

from __future__ import annotations

from business_quality import BusinessQualityAnalysis
from earnings_quality import EarningsQualityAnalysis, EarningsQualityEngine
from economic_moat import EconomicAnalysis, EconomicEngine
from financial import FinancialAnalysis
from financial_strength import FinancialStrengthAnalysis, FinancialStrengthEngine
from growth_quality import GrowthQualityAnalysis, GrowthQualityEngine
from management_quality import ManagementAnalysis, ManagementEngine

from business_quality_aggregator.adapters import extract_component_result
from business_quality_aggregator.conflicts import resolve_conflicts
from business_quality_aggregator.exceptions import (
    BusinessQualityAggregatorValidationError,
)
from business_quality_aggregator.explainability import (
    AGGREGATOR_RESEARCH_DISCLAIMER,
    aggregate_cross_domain_factors,
    analysis_confidence,
    build_explainability,
    build_investment_observations,
    build_recommendation,
    build_summary,
)
from business_quality_aggregator.metadata import (
    AGGREGATOR_VERSION,
    FRAMEWORK_VERSION,
    BusinessQualityAggregatorMetadata,
)
from business_quality_aggregator.models import (
    BusinessQualityAggregation,
    BusinessQualityAggregatorExplainability,
    BusinessQualityAggregatorScore,
    BusinessQualityAggregatorValidationSummary,
)
from business_quality_aggregator.scoring import (
    DEFAULT_AGGREGATOR_WEIGHTS,
    AggregatorComponent,
    BusinessQualityAggregatorWeights,
    aggregator_rating_from_score,
    validate_weights,
    weighted_mean,
)
from business_quality_aggregator.validation import validate_framework_inputs

__all__ = ["BusinessQualityAggregatorEngine"]


class BusinessQualityAggregatorEngine:
    """Aggregate five domain analyses into an explainable business-quality view."""

    def __init__(
        self, *, default_weights: BusinessQualityAggregatorWeights | None = None
    ) -> None:
        self._default_weights = validate_weights(
            default_weights or DEFAULT_AGGREGATOR_WEIGHTS
        )

    @property
    def version(self) -> str:
        return AGGREGATOR_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> BusinessQualityAggregatorWeights:
        return self._default_weights

    def validate(
        self,
        *,
        economic_moat: object | None = None,
        management_quality: object | None = None,
        financial_strength: object | None = None,
        earnings_quality: object | None = None,
        growth_quality: object | None = None,
        metadata: object | None = None,
    ) -> BusinessQualityAggregatorValidationSummary:
        effective_metadata = metadata if metadata is not None else self._metadata()
        return validate_framework_inputs(
            economic_moat=economic_moat,
            management_quality=management_quality,
            financial_strength=financial_strength,
            earnings_quality=earnings_quality,
            growth_quality=growth_quality,
            metadata=effective_metadata,
        )

    def analyze(
        self,
        *,
        economic_moat: EconomicAnalysis,
        management_quality: ManagementAnalysis,
        financial_strength: FinancialStrengthAnalysis,
        earnings_quality: EarningsQualityAnalysis,
        growth_quality: GrowthQualityAnalysis,
        metadata: BusinessQualityAggregatorMetadata | None = None,
        weights: BusinessQualityAggregatorWeights | None = None,
    ) -> BusinessQualityAggregation:
        effective_metadata = metadata if metadata is not None else self._metadata()
        effective_weights = validate_weights(weights or self._default_weights)
        validation = self.validate(
            economic_moat=economic_moat,
            management_quality=management_quality,
            financial_strength=financial_strength,
            earnings_quality=earnings_quality,
            growth_quality=growth_quality,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise BusinessQualityAggregatorValidationError(
                "; ".join(validation.errors)
            )

        components = (
            extract_component_result(
                component=AggregatorComponent.ECONOMIC_MOAT,
                analysis=economic_moat,
                weight=effective_weights.economic_moat,
                rating_attr="overall_moat_rating",
            ),
            extract_component_result(
                component=AggregatorComponent.MANAGEMENT_QUALITY,
                analysis=management_quality,
                weight=effective_weights.management_quality,
                rating_attr="overall_management_rating",
            ),
            extract_component_result(
                component=AggregatorComponent.FINANCIAL_STRENGTH,
                analysis=financial_strength,
                weight=effective_weights.financial_strength,
                rating_attr="overall_strength_rating",
            ),
            extract_component_result(
                component=AggregatorComponent.EARNINGS_QUALITY,
                analysis=earnings_quality,
                weight=effective_weights.earnings_quality,
                rating_attr="overall_earnings_rating",
            ),
            extract_component_result(
                component=AggregatorComponent.GROWTH_QUALITY,
                analysis=growth_quality,
                weight=effective_weights.growth_quality,
                rating_attr="overall_growth_rating",
            ),
        )
        pairs: list[tuple[float, float]] = []
        for component in components:
            if component.engine_score.value is None:
                continue
            pairs.append((component.engine_score.value, component.weight))
        raw = weighted_mean(pairs)
        conflict = resolve_conflicts(
            raw_score=raw,
            economic_moat=economic_moat,
            management_quality=management_quality,
            financial_strength=financial_strength,
            earnings_quality=earnings_quality,
            growth_quality=growth_quality,
        )
        overall = conflict.adjusted_score
        rating = aggregator_rating_from_score(overall)
        confidence = analysis_confidence(components)
        strengths, weaknesses, risks = aggregate_cross_domain_factors(components)
        explainability = build_explainability(
            effective_metadata,
            components,
            confidence,
            rating,
            overall,
            effective_weights,
            conflict.adjustments,
        )
        evidence = tuple(
            item for component in components for item in component.evidence
        ) + tuple(
            item
            for item in explainability.evidence
            if item.source == "ConflictResolution"
        )
        score = (
            BusinessQualityAggregatorScore(value=None, status="insufficient_data")
            if overall is None
            else BusinessQualityAggregatorScore(
                value=round(overall, 4), status="assessed"
            )
        )
        return BusinessQualityAggregation(
            metadata=effective_metadata,
            validation=validation,
            score=score,
            evidence=evidence,
            confidence=confidence,
            explainability=explainability,
            components=components,
            conflict_adjustments=conflict.adjustments,
            raw_weighted_score=None if raw is None else round(raw, 4),
            overall_business_quality_rating=rating,
            summary=build_summary(rating, overall, components, conflict.adjustments),
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            investment_observations=build_investment_observations(
                components, conflict.adjustments
            ),
            recommendation=build_recommendation(
                rating, confidence, conflict.adjustments
            ),
            weights_used=effective_weights,
            research_disclaimer=AGGREGATOR_RESEARCH_DISCLAIMER,
        )

    def analyze_from_inputs(
        self,
        financial_analysis: FinancialAnalysis,
        business_quality_analysis: BusinessQualityAnalysis,
        *,
        metadata: BusinessQualityAggregatorMetadata | None = None,
        weights: BusinessQualityAggregatorWeights | None = None,
    ) -> BusinessQualityAggregation:
        """Convenience: invoke public domain engines, then compose."""
        return self.analyze(
            economic_moat=EconomicEngine().analyze(
                financial_analysis, business_quality_analysis
            ),
            management_quality=ManagementEngine().analyze(
                financial_analysis, business_quality_analysis
            ),
            financial_strength=FinancialStrengthEngine().analyze(
                financial_analysis, business_quality_analysis
            ),
            earnings_quality=EarningsQualityEngine().analyze(
                financial_analysis, business_quality_analysis
            ),
            growth_quality=GrowthQualityEngine().analyze(
                financial_analysis, business_quality_analysis
            ),
            metadata=metadata,
            weights=weights,
        )

    def explain(
        self, analysis: BusinessQualityAggregation
    ) -> BusinessQualityAggregatorExplainability:
        if not isinstance(analysis, BusinessQualityAggregation):
            raise BusinessQualityAggregatorValidationError(
                f"Accept ONLY BusinessQualityAggregation, got {type(analysis).__name__}"
            )
        return analysis.explainability

    def _metadata(self) -> BusinessQualityAggregatorMetadata:
        return BusinessQualityAggregatorMetadata(engine_version=self.version)
