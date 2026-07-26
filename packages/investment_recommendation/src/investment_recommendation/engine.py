"""Public Investment Recommendation engine (FEATURE-007 Phase 1).

Distinct from G1.3 ``recommendation.RecommendationEngine``.
"""

from __future__ import annotations

from business_quality_aggregator import BusinessQualityAggregation
from earnings_quality import EarningsQualityAnalysis
from economic_moat import EconomicAnalysis
from financial_strength import FinancialStrengthAnalysis
from growth_quality import GrowthQualityAnalysis
from management_quality import ManagementAnalysis
from valuation import OverallValuationResult

from investment_recommendation.adapters import (
    extract_margin_of_safety,
    make_contribution,
    safe_confidence,
    safe_score_value,
)
from investment_recommendation.exceptions import (
    InvestmentRecommendationValidationError,
)
from investment_recommendation.explainability import (
    RESEARCH_DISCLAIMER,
    analysis_confidence,
    build_explainability,
    build_factors,
    build_recommendation_text,
    build_summary,
    build_thesis,
)
from investment_recommendation.metadata import (
    FRAMEWORK_VERSION,
    RECOMMENDATION_VERSION,
    InvestmentRecommendationMetadata,
)
from investment_recommendation.models import (
    InvestmentRecommendation,
    InvestmentRecommendationExplainability,
    InvestmentRecommendationScore,
    InvestmentRecommendationValidationSummary,
)
from investment_recommendation.rules import apply_decision_rules, cap_action
from investment_recommendation.scoring import (
    DEFAULT_DECISION_WEIGHTS,
    DecisionComponent,
    DecisionWeights,
    action_from_score,
    validate_weights,
    weighted_mean,
)
from investment_recommendation.validation import validate_framework_inputs
from investment_recommendation.valuation_signals import ValuationSignals

__all__ = ["InvestmentRecommendationEngine"]


class InvestmentRecommendationEngine:
    """Deterministic investment recommendation from public domain outputs."""

    def __init__(self, *, default_weights: DecisionWeights | None = None) -> None:
        self._default_weights = validate_weights(
            default_weights or DEFAULT_DECISION_WEIGHTS
        )

    @property
    def version(self) -> str:
        return RECOMMENDATION_VERSION

    @property
    def framework_version(self) -> str:
        return FRAMEWORK_VERSION

    @property
    def default_weights(self) -> DecisionWeights:
        return self._default_weights

    def validate(
        self,
        *,
        valuation: object | None = None,
        business_quality: object | None = None,
        economic_moat: object | None = None,
        management_quality: object | None = None,
        financial_strength: object | None = None,
        earnings_quality: object | None = None,
        growth_quality: object | None = None,
        metadata: object | None = None,
    ) -> InvestmentRecommendationValidationSummary:
        effective_metadata = metadata if metadata is not None else self._metadata()
        return validate_framework_inputs(
            valuation=valuation,
            business_quality=business_quality,
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
        valuation: OverallValuationResult | ValuationSignals,
        business_quality: BusinessQualityAggregation,
        economic_moat: EconomicAnalysis,
        management_quality: ManagementAnalysis,
        financial_strength: FinancialStrengthAnalysis,
        earnings_quality: EarningsQualityAnalysis,
        growth_quality: GrowthQualityAnalysis,
        metadata: InvestmentRecommendationMetadata | None = None,
        weights: DecisionWeights | None = None,
    ) -> InvestmentRecommendation:
        effective_metadata = metadata if metadata is not None else self._metadata()
        effective_weights = validate_weights(weights or self._default_weights)
        validation = self.validate(
            valuation=valuation,
            business_quality=business_quality,
            economic_moat=economic_moat,
            management_quality=management_quality,
            financial_strength=financial_strength,
            earnings_quality=earnings_quality,
            growth_quality=growth_quality,
            metadata=effective_metadata,
        )
        if not validation.ok:
            raise InvestmentRecommendationValidationError(
                "; ".join(validation.errors)
            )

        quality = safe_score_value(business_quality)
        moat = safe_score_value(economic_moat)
        mgmt = safe_score_value(management_quality)
        strength = safe_score_value(financial_strength)
        earnings = safe_score_value(earnings_quality)
        growth = safe_score_value(growth_quality)
        bq_conf = safe_confidence(business_quality)
        mos = extract_margin_of_safety(
            valuation, business_quality_confidence=bq_conf
        )

        contributions = (
            make_contribution(
                DecisionComponent.BUSINESS_QUALITY,
                quality,
                weight=effective_weights.business_quality,
                confidence=bq_conf,
            ),
            make_contribution(
                DecisionComponent.VALUATION_MOS,
                mos.valuation_score,
                weight=effective_weights.valuation_mos,
                confidence=mos.valuation_confidence,
            ),
            make_contribution(
                DecisionComponent.ECONOMIC_MOAT,
                moat,
                weight=effective_weights.economic_moat,
                confidence=safe_confidence(economic_moat),
            ),
            make_contribution(
                DecisionComponent.MANAGEMENT_QUALITY,
                mgmt,
                weight=effective_weights.management_quality,
                confidence=safe_confidence(management_quality),
            ),
            make_contribution(
                DecisionComponent.FINANCIAL_STRENGTH,
                strength,
                weight=effective_weights.financial_strength,
                confidence=safe_confidence(financial_strength),
            ),
            make_contribution(
                DecisionComponent.EARNINGS_QUALITY,
                earnings,
                weight=effective_weights.earnings_quality,
                confidence=safe_confidence(earnings_quality),
            ),
            make_contribution(
                DecisionComponent.GROWTH_QUALITY,
                growth,
                weight=effective_weights.growth_quality,
                confidence=safe_confidence(growth_quality),
            ),
        )
        pairs = [
            (c.score.value, c.weight)
            for c in contributions
            if c.score.value is not None
        ]
        raw = weighted_mean(pairs)
        rule_result = apply_decision_rules(
            raw_score=raw,
            quality=quality,
            moat=moat,
            management=mgmt,
            strength=strength,
            earnings=earnings,
            growth=growth,
            mos=mos,
        )
        overall = rule_result.adjusted_score
        action = cap_action(
            action_from_score(overall), rule_result.action_cap
        )
        confidence = analysis_confidence(contributions, mos)
        positives, negatives, risks, drivers = build_factors(
            contributions, rule_result.rules, mos
        )
        explainability = build_explainability(
            effective_metadata,
            contributions,
            confidence,
            action,
            overall,
            effective_weights,
            rule_result.rules,
            mos,
        )
        score = (
            InvestmentRecommendationScore(value=None, status="insufficient_data")
            if overall is None
            else InvestmentRecommendationScore(
                value=round(overall, 4), status="assessed"
            )
        )
        return InvestmentRecommendation(
            metadata=effective_metadata,
            validation=validation,
            score=score,
            recommendation=action,
            confidence=confidence,
            evidence=explainability.evidence,
            explainability=explainability,
            contributions=contributions,
            triggered_rules=rule_result.rules,
            margin_of_safety=mos,
            raw_score=None if raw is None else round(raw, 4),
            positive_factors=positives,
            negative_factors=negatives,
            risks=risks,
            key_drivers=drivers,
            investment_thesis=build_thesis(action, quality, mos),
            decision_summary=build_summary(
                action, overall, mos, rule_result.rules
            ),
            recommendation_text=build_recommendation_text(action, confidence),
            weights_used=effective_weights,
            research_disclaimer=RESEARCH_DISCLAIMER,
        )

    def explain(
        self, analysis: InvestmentRecommendation
    ) -> InvestmentRecommendationExplainability:
        if not isinstance(analysis, InvestmentRecommendation):
            raise InvestmentRecommendationValidationError(
                "Accept ONLY InvestmentRecommendation, "
                f"got {type(analysis).__name__}"
            )
        return analysis.explainability

    def _metadata(self) -> InvestmentRecommendationMetadata:
        return InvestmentRecommendationMetadata(engine_version=self.version)
