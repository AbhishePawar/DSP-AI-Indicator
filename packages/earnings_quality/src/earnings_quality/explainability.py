"""Explainability builders for Earnings Quality Intelligence."""

from __future__ import annotations

from earnings_quality.metadata import EarningsQualityMetadata
from earnings_quality.models import (
    EarningsQualityAnalysis,
    EarningsQualityComponentScore,
    EarningsQualityConfidence,
    EarningsQualityEvidence,
    EarningsQualityExplainability,
)
from earnings_quality.scoring import EarningsQualityRating

__all__ = [
    "EARNINGS_QUALITY_RESEARCH_DISCLAIMER",
    "aggregate_factors",
    "analysis_confidence",
    "build_earnings_explainability",
    "build_recommendation",
    "build_summary",
]

EARNINGS_QUALITY_RESEARCH_DISCLAIMER = (
    "Earnings Quality Intelligence provides research-only, evidence-backed "
    "assessments of earnings quality, predictability, and sustainability. It is "
    "not investment advice, an audit opinion, or a forensic accounting conclusion. "
    "Scores are rule-based proxies from FinancialAnalysis and BusinessQualityAnalysis."
)


def build_summary(
    rating: EarningsQualityRating,
    score: float | None,
    components: tuple[EarningsQualityComponentScore, ...],
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
        f"Overall earnings quality rating is {rating.value} "
        f"(score {score_txt}) across six Buffett-aligned dimensions."
        f"{strong_txt}{weak_txt} "
        "Interpretation prioritises cash-backed, consistent, predictable earnings."
    )


def build_recommendation(
    rating: EarningsQualityRating, confidence: EarningsQualityConfidence
) -> str:
    if confidence.value < 0.35:
        return (
            "Insufficient evidence confidence for a firm earnings-quality "
            "conclusion; treat scores as provisional research hypotheses only."
        )
    mapping = {
        EarningsQualityRating.EXCELLENT: (
            "Evidence is consistent with high-quality, predictable earnings. "
            "Still verify exceptional items and accounting footnotes in filings."
        ),
        EarningsQualityRating.GOOD: (
            "Evidence supports good earnings quality. Monitor cash conversion "
            "and margin stability through the cycle."
        ),
        EarningsQualityRating.AVERAGE: (
            "Evidence suggests average earnings quality. Focus diligence on "
            "accruals, one-time items, and cyclicality."
        ),
        EarningsQualityRating.POOR: (
            "Evidence points to poor earnings quality. Demand a higher margin "
            "of safety and deeper cash-flow reconciliation."
        ),
        EarningsQualityRating.VERY_POOR: (
            "Evidence does not support high earnings quality. Avoid assuming "
            "predictable or cash-backed profits."
        ),
    }
    return mapping[rating]


def build_earnings_explainability(
    metadata: EarningsQualityMetadata,
    components: tuple[EarningsQualityComponentScore, ...],
    confidence: EarningsQualityConfidence,
    rating: EarningsQualityRating,
    score: float | None,
) -> EarningsQualityExplainability:
    evidence: list[EarningsQualityEvidence] = []
    for component in components:
        evidence.extend(component.evidence)
    return EarningsQualityExplainability(
        evidence=tuple(evidence),
        confidence=confidence,
        assumptions=(
            "FinancialAnalysis and BusinessQualityAnalysis are accepted public inputs.",
            "Dimension scores are deterministic functions of documented proxies.",
            f"Framework version: {metadata.framework_version}.",
            "Buffett alignment: predictable, cash-backed, conservatively accounted earnings.",
        ),
        limitations=(
            "No restatement registry or forensic audit in Phase 1.",
            "Predictability uses historical stability — not a forward forecast model.",
            "Not an auditor opinion or investment recommendation.",
            "Future AI-assisted analysis may enrich evidence without changing contracts.",
        ),
        reasoning=build_summary(rating, score, components),
    )


def aggregate_factors(
    components: tuple[EarningsQualityComponentScore, ...],
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
    components: tuple[EarningsQualityComponentScore, ...],
) -> EarningsQualityConfidence:
    values = [c.confidence.value for c in components if c.score.value is not None]
    if not values:
        return EarningsQualityConfidence(
            value=0.0, basis="insufficient_component_scores"
        )
    return EarningsQualityConfidence(
        value=round(sum(values) / len(values), 4),
        basis="mean_component_confidence",
    )


def explain_from_analysis(analysis: EarningsQualityAnalysis) -> EarningsQualityExplainability:
    return analysis.explainability
