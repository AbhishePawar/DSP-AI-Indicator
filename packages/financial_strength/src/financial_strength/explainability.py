"""Explainability builders for Financial Strength Intelligence."""

from __future__ import annotations

from financial_strength.metadata import FinancialStrengthMetadata
from financial_strength.models import (
    FinancialStrengthAnalysis,
    FinancialStrengthComponentScore,
    FinancialStrengthConfidence,
    FinancialStrengthEvidence,
    FinancialStrengthExplainability,
)
from financial_strength.scoring import FinancialStrengthRating

__all__ = [
    "FINANCIAL_STRENGTH_RESEARCH_DISCLAIMER",
    "aggregate_factors",
    "analysis_confidence",
    "build_recommendation",
    "build_strength_explainability",
    "build_summary",
]

FINANCIAL_STRENGTH_RESEARCH_DISCLAIMER = (
    "Financial Strength Intelligence provides research-only, evidence-backed "
    "assessments of balance-sheet quality and financial resilience. It is not "
    "investment advice, a credit rating, or a guarantee of solvency. Scores are "
    "rule-based proxies from FinancialAnalysis and BusinessQualityAnalysis."
)


def build_summary(
    rating: FinancialStrengthRating,
    score: float | None,
    components: tuple[FinancialStrengthComponentScore, ...],
) -> str:
    score_txt = "n/a" if score is None else f"{score:.1f}/100"
    strongest = max(
        (c for c in components if c.score.value is not None),
        key=lambda c: c.score.value or 0.0,
        default=None,
    )
    weakest = min(
        (c for c in components if c.score.value is not None),
        key=lambda c: c.score.value or 0.0,
        default=None,
    )
    strong_txt = (
        f" Strongest dimension: {strongest.dimension.value}."
        if strongest is not None
        else ""
    )
    weak_txt = (
        f" Weakest dimension: {weakest.dimension.value}."
        if weakest is not None
        else ""
    )
    return (
        f"Overall financial strength rating is {rating.value} "
        f"(score {score_txt}) across six Buffett-aligned dimensions."
        f"{strong_txt}{weak_txt} "
        "Interpretation prioritises conservative leverage, cash generation, "
        "and financial flexibility."
    )


def build_recommendation(
    rating: FinancialStrengthRating, confidence: FinancialStrengthConfidence
) -> str:
    if confidence.value < 0.35:
        return (
            "Insufficient evidence confidence for a firm financial-strength "
            "conclusion; treat scores as provisional research hypotheses only."
        )
    mapping = {
        FinancialStrengthRating.EXCEPTIONAL: (
            "Evidence is consistent with a fortress balance sheet and strong "
            "cash generation. Verify maturity profile and off-balance items in filings."
        ),
        FinancialStrengthRating.STRONG: (
            "Evidence supports strong financial strength. Monitor leverage and "
            "liquidity through the cycle."
        ),
        FinancialStrengthRating.AVERAGE: (
            "Evidence suggests average financial strength. Focus diligence on "
            "debt service capacity and cash conversion."
        ),
        FinancialStrengthRating.WEAK: (
            "Evidence points to weak financial strength. Demand a higher margin "
            "of safety and review refinancing risk."
        ),
        FinancialStrengthRating.VERY_WEAK: (
            "Evidence does not support financial strength. Avoid assuming "
            "balance-sheet durability or cash flexibility."
        ),
    }
    return mapping[rating]


def build_strength_explainability(
    metadata: FinancialStrengthMetadata,
    components: tuple[FinancialStrengthComponentScore, ...],
    confidence: FinancialStrengthConfidence,
    rating: FinancialStrengthRating,
    score: float | None,
) -> FinancialStrengthExplainability:
    evidence: list[FinancialStrengthEvidence] = []
    for component in components:
        evidence.extend(component.evidence)
    return FinancialStrengthExplainability(
        evidence=tuple(evidence),
        confidence=confidence,
        assumptions=(
            "FinancialAnalysis and BusinessQualityAnalysis are accepted public inputs.",
            "Dimension scores are deterministic functions of documented proxies.",
            f"Framework version: {metadata.framework_version}.",
            "Buffett alignment: conservative balance sheets, cash generation, flexibility.",
        ),
        limitations=(
            "Debt maturity schedules and full stress histories are limited in Phase 1.",
            "Not a formal credit rating or regulatory capital assessment.",
            "Does not forecast prices or issue buy/sell advice.",
            "Future AI-assisted analysis may enrich evidence without changing contracts.",
        ),
        reasoning=build_summary(rating, score, components),
    )


def aggregate_factors(
    components: tuple[FinancialStrengthComponentScore, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    risks: list[str] = []
    key_metrics: list[str] = []
    for component in components:
        strengths.extend(component.positive_factors)
        weaknesses.extend(component.negative_factors)
        risks.extend(component.risks)
        key_metrics.extend(component.key_metrics)
    return (
        tuple(strengths),
        tuple(weaknesses),
        tuple(risks),
        tuple(key_metrics),
    )


def analysis_confidence(
    components: tuple[FinancialStrengthComponentScore, ...],
) -> FinancialStrengthConfidence:
    values = [c.confidence.value for c in components if c.score.value is not None]
    if not values:
        return FinancialStrengthConfidence(
            value=0.0, basis="insufficient_component_scores"
        )
    mean = sum(values) / len(values)
    return FinancialStrengthConfidence(
        value=round(mean, 4),
        basis="mean_component_confidence",
    )


def explain_from_analysis(
    analysis: FinancialStrengthAnalysis,
) -> FinancialStrengthExplainability:
    return analysis.explainability
