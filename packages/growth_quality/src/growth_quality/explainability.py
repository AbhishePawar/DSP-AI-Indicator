"""Explainability builders for Growth Quality Intelligence."""

from __future__ import annotations

from growth_quality.metadata import GrowthQualityMetadata
from growth_quality.models import (
    GrowthQualityComponentScore,
    GrowthQualityConfidence,
    GrowthQualityEvidence,
    GrowthQualityExplainability,
)
from growth_quality.scoring import GrowthQualityRating

__all__ = [
    "GROWTH_QUALITY_RESEARCH_DISCLAIMER",
    "aggregate_factors",
    "analysis_confidence",
    "build_growth_explainability",
    "build_recommendation",
    "build_summary",
]

GROWTH_QUALITY_RESEARCH_DISCLAIMER = (
    "Growth Quality Intelligence provides research-only, evidence-backed "
    "assessments of growth durability and reinvestment efficiency. It is not "
    "investment advice or a growth forecast. Scores are rule-based proxies from "
    "FinancialAnalysis and BusinessQualityAnalysis; leverage- or dilution-driven "
    "expansion is not rewarded when proxies indicate elevated risk."
)


def build_summary(
    rating: GrowthQualityRating,
    score: float | None,
    components: tuple[GrowthQualityComponentScore, ...],
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
        f"Overall growth quality rating is {rating.value} "
        f"(score {score_txt}) across six Buffett-aligned dimensions."
        f"{strong_txt}{weak_txt} "
        "Interpretation prioritises sustainable compounding and high-return reinvestment."
    )


def build_recommendation(
    rating: GrowthQualityRating, confidence: GrowthQualityConfidence
) -> str:
    if confidence.value < 0.35:
        return (
            "Insufficient evidence confidence for a firm growth-quality conclusion; "
            "treat scores as provisional research hypotheses only."
        )
    mapping = {
        GrowthQualityRating.EXCEPTIONAL: (
            "Evidence is consistent with high-quality, capital-efficient compounding. "
            "Still verify organic vs acquisition attribution in filings."
        ),
        GrowthQualityRating.STRONG: (
            "Evidence supports strong growth quality. Monitor ROIC versus growth "
            "and funding mix through the cycle."
        ),
        GrowthQualityRating.MODERATE: (
            "Evidence suggests moderate growth quality. Focus diligence on "
            "reinvestment returns and leverage/dilution risk."
        ),
        GrowthQualityRating.WEAK: (
            "Evidence points to weak growth quality. Demand a higher margin of "
            "safety and scrutinise acquisition- or debt-funded expansion."
        ),
        GrowthQualityRating.VERY_WEAK: (
            "Evidence does not support high-quality growth. Avoid assuming "
            "sustainable compounding or capital-efficient expansion."
        ),
    }
    return mapping[rating]


def build_growth_explainability(
    metadata: GrowthQualityMetadata,
    components: tuple[GrowthQualityComponentScore, ...],
    confidence: GrowthQualityConfidence,
    rating: GrowthQualityRating,
    score: float | None,
) -> GrowthQualityExplainability:
    evidence: list[GrowthQualityEvidence] = []
    for component in components:
        evidence.extend(component.evidence)
    return GrowthQualityExplainability(
        evidence=tuple(evidence),
        confidence=confidence,
        assumptions=(
            "FinancialAnalysis and BusinessQualityAnalysis are accepted public inputs.",
            "Dimension scores are deterministic functions of documented proxies.",
            f"Framework version: {metadata.framework_version}.",
            "Buffett alignment: sustainable compounding, high-return reinvestment, "
            "organic growth preference.",
        ),
        limitations=(
            "Customer concentration and market saturation feeds deferred.",
            "Organic vs acquisition growth is proxied, not deal-attributed.",
            "Not a revenue or EPS forecast.",
            "Future AI-assisted analysis may enrich evidence without changing contracts.",
        ),
        reasoning=build_summary(rating, score, components),
    )


def aggregate_factors(
    components: tuple[GrowthQualityComponentScore, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    risks: list[str] = []
    for component in components:
        strengths.extend(component.positive_factors)
        weaknesses.extend(component.negative_factors)
        risks.extend(component.risks)
    return tuple(strengths), tuple(weaknesses), tuple(risks)


def analysis_confidence(
    components: tuple[GrowthQualityComponentScore, ...],
) -> GrowthQualityConfidence:
    values = [c.confidence.value for c in components if c.score.value is not None]
    if not values:
        return GrowthQualityConfidence(
            value=0.0, basis="insufficient_component_scores"
        )
    return GrowthQualityConfidence(
        value=round(sum(values) / len(values), 4),
        basis="mean_component_confidence",
    )
