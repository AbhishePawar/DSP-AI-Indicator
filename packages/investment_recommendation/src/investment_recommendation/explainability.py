"""Explainability builders for Investment Recommendation."""

from __future__ import annotations

from investment_recommendation.metadata import InvestmentRecommendationMetadata
from investment_recommendation.models import (
    DecisionContribution,
    InvestmentRecommendationConfidence,
    InvestmentRecommendationEvidence,
    InvestmentRecommendationExplainability,
    MarginOfSafetyAssessment,
    TriggeredRule,
)
from investment_recommendation.scoring import (
    DecisionWeights,
    InvestmentRecommendationAction,
)

__all__ = [
    "RESEARCH_DISCLAIMER",
    "analysis_confidence",
    "build_explainability",
    "build_factors",
    "build_recommendation_text",
    "build_summary",
    "build_thesis",
]

RESEARCH_DISCLAIMER = (
    "Investment Recommendation Engine produces research-only, deterministic "
    "decision intelligence from public valuation and domain-quality engines. "
    "It is not investment advice, not AI Committee output, and not a broker order. "
    "Strong Buy is blocked when price is materially above conservative intrinsic value."
)


def build_summary(
    action: InvestmentRecommendationAction,
    score: float | None,
    mos: MarginOfSafetyAssessment,
    rules: tuple[TriggeredRule, ...],
) -> str:
    score_txt = "n/a" if score is None else f"{score:.1f}/100"
    return (
        f"Recommendation is {action.value.replace('_', ' ')} "
        f"(investment score {score_txt}). "
        f"MoS classification: {mos.classification}. "
        f"{mos.reasoning} "
        f"Triggered {len(rules)} decision rule(s)."
    )


def build_thesis(
    action: InvestmentRecommendationAction,
    quality: float | None,
    mos: MarginOfSafetyAssessment,
) -> str:
    q = "n/a" if quality is None else f"{quality:.1f}"
    mos_txt = "n/a" if mos.margin_of_safety is None else f"{mos.margin_of_safety:.1%}"
    return (
        f"Thesis ({action.value}): business-quality composite {q}/100 with "
        f"margin of safety {mos_txt} "
        f"(IV/share={mos.intrinsic_value_per_share}, price={mos.current_market_price}). "
        "Decision prioritises durable quality and a documented MoS buffer."
    )


def build_recommendation_text(
    action: InvestmentRecommendationAction,
    confidence: InvestmentRecommendationConfidence,
) -> str:
    if action is InvestmentRecommendationAction.UNAVAILABLE:
        return (
            "Recommendation unavailable — insufficient evidence to form a "
            "directional research posture. No HOLD is inferred from missing inputs."
        )
    if confidence.value < 0.35:
        return (
            "Low decision confidence — treat the recommendation as provisional "
            "research only and re-check valuation/quality inputs."
        )
    labels = {
        InvestmentRecommendationAction.STRONG_BUY: (
            "Evidence supports a Strong Buy research posture given quality and MoS."
        ),
        InvestmentRecommendationAction.BUY: (
            "Evidence supports a Buy research posture."
        ),
        InvestmentRecommendationAction.ACCUMULATE: (
            "Evidence supports an Accumulate posture — scale in patiently."
        ),
        InvestmentRecommendationAction.HOLD: (
            "Evidence supports a Hold posture — wait for better MoS or quality clarity."
        ),
        InvestmentRecommendationAction.REDUCE: (
            "Evidence supports a Reduce posture — trim exposure in research framing."
        ),
        InvestmentRecommendationAction.SELL: (
            "Evidence supports a Sell research posture."
        ),
        InvestmentRecommendationAction.STRONG_SELL: (
            "Evidence supports a Strong Sell research posture."
        ),
    }
    return labels[action]


def build_factors(
    contributions: tuple[DecisionContribution, ...],
    rules: tuple[TriggeredRule, ...],
    mos: MarginOfSafetyAssessment,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    positives: list[str] = []
    negatives: list[str] = []
    risks: list[str] = []
    drivers: list[str] = []
    for c in contributions:
        if c.score.value is None:
            continue
        drivers.append(
            f"{c.component.value}={c.score.value:.1f} (w={c.weight:.2f})"
        )
        if c.score.value >= 70:
            positives.append(f"Strong {c.component.value} contribution")
        elif c.score.value < 45:
            negatives.append(f"Weak {c.component.value} contribution")
    if mos.classification in {"deep_value", "undervalued"}:
        positives.append(f"Attractive MoS ({mos.classification})")
    elif mos.classification in {"overvalued", "extremely_overvalued"}:
        negatives.append(f"Unattractive MoS ({mos.classification})")
        risks.append("Paying above conservative intrinsic value")
    for rule in rules:
        if rule.score_delta < 0:
            risks.append(rule.description)
            negatives.append(f"Rule {rule.rule_id}")
        elif rule.score_delta > 0:
            positives.append(f"Rule {rule.rule_id}")
    return tuple(positives), tuple(negatives), tuple(risks), tuple(drivers)


def build_explainability(
    metadata: InvestmentRecommendationMetadata,
    contributions: tuple[DecisionContribution, ...],
    confidence: InvestmentRecommendationConfidence,
    action: InvestmentRecommendationAction,
    score: float | None,
    weights: DecisionWeights,
    rules: tuple[TriggeredRule, ...],
    mos: MarginOfSafetyAssessment,
) -> InvestmentRecommendationExplainability:
    evidence: list[InvestmentRecommendationEvidence] = [
        InvestmentRecommendationEvidence(
            source="OverallValuationResult",
            reference="margin_of_safety",
            summary=mos.classification,
            reasoning=mos.reasoning,
            confidence=mos.valuation_confidence,
            supporting_metrics=(
                f"ivps={mos.intrinsic_value_per_share}",
                f"price={mos.current_market_price}",
                f"mos={mos.margin_of_safety}",
                f"premium_discount={mos.premium_discount}",
            ),
            limitations=("IV is model-based and research-only.",),
            contributing_engines=("valuation",),
        )
    ]
    for c in contributions:
        if c.score.value is None:
            continue
        evidence.append(
            InvestmentRecommendationEvidence(
                source="DecisionContribution",
                reference=c.component.value,
                summary=f"Contribution score {c.score.value:.1f}",
                reasoning=f"Weighted by {c.weight:.2f} in the decision blend.",
                confidence=c.confidence.value,
                supporting_metrics=(
                    f"score={c.score.value}",
                    f"weight={c.weight}",
                    f"contribution={c.weighted_contribution}",
                ),
                limitations=("Domain scores are upstream proxies.",),
                contributing_engines=(c.component.value,),
            )
        )
    for rule in rules:
        evidence.append(
            InvestmentRecommendationEvidence(
                source="DecisionRule",
                reference=rule.rule_id,
                summary=rule.description,
                reasoning=(
                    f"Group={rule.group}; score_delta={rule.score_delta}; "
                    f"action_cap={rule.action_cap.value if rule.action_cap else None}."
                ),
                confidence=confidence.value,
                supporting_metrics=rule.supporting_metrics,
                limitations=("Rules are deterministic heuristics, not forecasts.",),
                contributing_engines=rule.engines,
            )
        )
    return InvestmentRecommendationExplainability(
        evidence=tuple(evidence),
        confidence=confidence,
        assumptions=(
            "Public OverallValuationResult and domain analyses are accepted inputs.",
            "No LLM / ML / AI Committee in this engine.",
            f"Framework version: {metadata.framework_version}.",
        ),
        limitations=(
            "Distinct from G1.3 packages/recommendation RecommendationEngine.",
            "Not investment advice; research-only decision intelligence.",
            "Platform / API / AI Committee composition deferred.",
        ),
        reasoning=build_summary(action, score, mos, rules),
        engine_weights=weights.as_dict(),
        decision_rules_triggered=tuple(r.rule_id for r in rules),
    )


def analysis_confidence(
    contributions: tuple[DecisionContribution, ...],
    mos: MarginOfSafetyAssessment,
) -> InvestmentRecommendationConfidence:
    values = [c.confidence.value for c in contributions if c.data_available]
    if not values:
        return InvestmentRecommendationConfidence(
            value=0.0, basis="insufficient_inputs"
        )
    coverage = sum(1 for c in contributions if c.data_available) / len(contributions)
    mean_conf = sum(values) / len(values)
    mos_factor = 1.0 if mos.margin_of_safety is not None else 0.75
    return InvestmentRecommendationConfidence(
        value=round(mean_conf * (0.65 + 0.35 * coverage) * mos_factor, 4),
        basis="mean_contribution_confidence_x_coverage_x_mos",
    )
