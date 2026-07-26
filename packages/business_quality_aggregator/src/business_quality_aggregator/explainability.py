"""Explainability builders for Business Quality Aggregator."""

from __future__ import annotations

from business_quality_aggregator.metadata import BusinessQualityAggregatorMetadata
from business_quality_aggregator.models import (
    AggregatorComponentResult,
    BusinessQualityAggregatorConfidence,
    BusinessQualityAggregatorEvidence,
    BusinessQualityAggregatorExplainability,
    ConflictAdjustment,
)
from business_quality_aggregator.scoring import (
    BusinessQualityAggregatorRating,
    BusinessQualityAggregatorWeights,
)

__all__ = [
    "AGGREGATOR_RESEARCH_DISCLAIMER",
    "aggregate_cross_domain_factors",
    "analysis_confidence",
    "build_explainability",
    "build_investment_observations",
    "build_recommendation",
    "build_summary",
]

AGGREGATOR_RESEARCH_DISCLAIMER = (
    "Business Quality Aggregator combines public outputs of Economic Moat, "
    "Management Quality, Financial Strength, Earnings Quality, and Growth Quality "
    "engines into a single research-only assessment. It is not investment advice. "
    "Cross-domain conflict penalties favour durable moats, owner-oriented management, "
    "financial conservatism, cash-backed earnings, and high-quality growth."
)


def build_summary(
    rating: BusinessQualityAggregatorRating,
    score: float | None,
    components: tuple[AggregatorComponentResult, ...],
    conflicts: tuple[ConflictAdjustment, ...],
) -> str:
    score_txt = "n/a" if score is None else f"{score:.1f}/100"
    strongest = max(
        (c for c in components if c.engine_score.value is not None),
        key=lambda c: c.engine_score.value or 0.0,
        default=None,
    )
    weakest = min(
        (c for c in components if c.engine_score.value is not None),
        key=lambda c: c.engine_score.value or 0.0,
        default=None,
    )
    strong_txt = (
        f" Strongest engine: {strongest.component.value}."
        if strongest is not None
        else ""
    )
    weak_txt = (
        f" Weakest engine: {weakest.component.value}."
        if weakest is not None
        else ""
    )
    conflict_txt = (
        f" Applied {len(conflicts)} cross-domain conflict adjustment(s)."
        if conflicts
        else " No cross-domain conflict penalties applied."
    )
    return (
        f"Overall business quality rating is {rating.value} "
        f"(score {score_txt}) across five domain engines."
        f"{strong_txt}{weak_txt}{conflict_txt} "
        "Interpretation prioritises durable advantages and capital-efficient compounding."
    )


def build_recommendation(
    rating: BusinessQualityAggregatorRating,
    confidence: BusinessQualityAggregatorConfidence,
    conflicts: tuple[ConflictAdjustment, ...],
) -> str:
    if confidence.value < 0.35:
        return (
            "Insufficient cross-domain confidence for a firm business-quality "
            "conclusion; treat the aggregation as provisional research only."
        )
    conflict_note = (
        f" Resolve noted conflicts ({', '.join(c.rule_id for c in conflicts[:3])})"
        " before relying on the composite."
        if conflicts
        else ""
    )
    mapping = {
        BusinessQualityAggregatorRating.EXCEPTIONAL: (
            "Evidence across domains is consistent with exceptional business quality "
            "for long-term compounding research."
        ),
        BusinessQualityAggregatorRating.EXCELLENT: (
            "Evidence supports excellent business quality. Monitor conflicting "
            "signals through the cycle."
        ),
        BusinessQualityAggregatorRating.GOOD: (
            "Evidence supports good business quality with room for domain-level diligence."
        ),
        BusinessQualityAggregatorRating.AVERAGE: (
            "Evidence suggests average business quality. Focus on the weakest engines "
            "and any conflict adjustments."
        ),
        BusinessQualityAggregatorRating.BELOW_AVERAGE: (
            "Evidence points to below-average business quality. Demand a higher "
            "margin of safety in research framing."
        ),
        BusinessQualityAggregatorRating.POOR: (
            "Evidence does not support high business quality. Avoid assuming durable "
            "compounding without resolving domain weaknesses."
        ),
    }
    return mapping[rating] + conflict_note


def build_investment_observations(
    components: tuple[AggregatorComponentResult, ...],
    conflicts: tuple[ConflictAdjustment, ...],
) -> tuple[str, ...]:
    observations: list[str] = []
    for component in components:
        if component.engine_score.value is None:
            observations.append(
                f"{component.component.value}: score unavailable — contribution excluded."
            )
            continue
        observations.append(
            f"{component.component.value}: score={component.engine_score.value:.1f}, "
            f"weight={component.weight:.2f}, contribution="
            f"{component.weighted_contribution}."
        )
    for conflict in conflicts:
        observations.append(
            f"Conflict {conflict.rule_id}: −{conflict.penalty_points:.1f} pts — "
            f"{conflict.description}"
        )
    return tuple(observations)


def build_explainability(
    metadata: BusinessQualityAggregatorMetadata,
    components: tuple[AggregatorComponentResult, ...],
    confidence: BusinessQualityAggregatorConfidence,
    rating: BusinessQualityAggregatorRating,
    score: float | None,
    weights: BusinessQualityAggregatorWeights,
    conflicts: tuple[ConflictAdjustment, ...],
) -> BusinessQualityAggregatorExplainability:
    evidence: list[BusinessQualityAggregatorEvidence] = []
    for component in components:
        evidence.extend(component.evidence)
    for conflict in conflicts:
        evidence.append(
            BusinessQualityAggregatorEvidence(
                source="ConflictResolution",
                reference=conflict.rule_id,
                summary=conflict.description,
                reasoning=(
                    f"Deterministic conflict penalty of {conflict.penalty_points} "
                    "points applied to the weighted aggregate."
                ),
                confidence=confidence.value,
                supporting_metrics=conflict.supporting_metrics,
                limitations=("Conflict rules are heuristic proxies, not forecasts.",),
                contributing_engines=conflict.engines,
            )
        )
    availability = tuple(
        f"{c.component.value}:{'available' if c.data_available else 'unavailable'}"
        for c in components
    )
    return BusinessQualityAggregatorExplainability(
        evidence=tuple(evidence),
        confidence=confidence,
        assumptions=(
            "Domain engine outputs are accepted public inputs (no re-scoring).",
            "Weights are configurable and must sum to 1.0.",
            "Conflict penalties are capped and fully enumerated.",
            f"Framework version: {metadata.framework_version}.",
        ),
        limitations=(
            "Distinct from F3.7 business_quality.BusinessQualityAggregator "
            "(which packages F3.6 analysis only).",
            "Does not run valuation, portfolio, or recommendation logic.",
            "Platform / API / AI Committee composition deferred.",
            "Conflict rules use public scores/components only.",
        ),
        reasoning=build_summary(rating, score, components, conflicts),
        engine_weights=weights.as_dict(),
        data_availability=availability,
    )


def aggregate_cross_domain_factors(
    components: tuple[AggregatorComponentResult, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    risks: list[str] = []
    for component in components:
        label = component.component.value
        for item in component.strengths[:3]:
            strengths.append(f"[{label}] {item}")
        for item in component.weaknesses[:3]:
            weaknesses.append(f"[{label}] {item}")
        for item in component.risks[:3]:
            risks.append(f"[{label}] {item}")
    return tuple(strengths), tuple(weaknesses), tuple(risks)


def analysis_confidence(
    components: tuple[AggregatorComponentResult, ...],
) -> BusinessQualityAggregatorConfidence:
    values = [
        c.engine_confidence.value
        for c in components
        if c.engine_score.value is not None
    ]
    if not values:
        return BusinessQualityAggregatorConfidence(
            value=0.0, basis="insufficient_component_scores"
        )
    available = sum(1 for c in components if c.data_available)
    coverage = available / len(components) if components else 0.0
    mean_conf = sum(values) / len(values)
    return BusinessQualityAggregatorConfidence(
        value=round(mean_conf * (0.7 + 0.3 * coverage), 4),
        basis="mean_engine_confidence_x_coverage",
    )
