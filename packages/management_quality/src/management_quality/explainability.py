"""Explainability builders for Management Quality Intelligence."""

from __future__ import annotations

from management_quality.metadata import ManagementMetadata
from management_quality.models import (
    ManagementAnalysis,
    ManagementConfidence,
    ManagementEvidence,
    ManagementExplainability,
    ManagementComponentScore,
)
from management_quality.scoring import ManagementRating

__all__ = [
    "MANAGEMENT_QUALITY_RESEARCH_DISCLAIMER",
    "aggregate_factors",
    "analysis_confidence",
    "build_management_explainability",
    "build_recommendation",
    "build_summary",
]

MANAGEMENT_QUALITY_RESEARCH_DISCLAIMER = (
    "Management Quality Intelligence provides research-only, evidence-backed "
    "assessments of management behaviour and capital allocation. It is not "
    "investment advice, a buy/sell recommendation, or a judgment of personal "
    "character. Scores are rule-based proxies from FinancialAnalysis and "
    "BusinessQualityAnalysis; unsupported qualitative claims are avoided."
)


def build_summary(
    rating: ManagementRating,
    score: float | None,
    components: tuple[ManagementComponentScore, ...],
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
        f"Overall management quality rating is {rating.value} "
        f"(score {score_txt}) across six Buffett/Munger-aligned dimensions."
        f"{strong_txt}{weak_txt} "
        "Interpretation prioritises rational capital allocation, honesty, "
        "conservative financing, and long-term value creation."
    )


def build_recommendation(
    rating: ManagementRating, confidence: ManagementConfidence
) -> str:
    if confidence.value < 0.35:
        return (
            "Insufficient evidence confidence for a firm management conclusion; "
            "treat scores as provisional research hypotheses only."
        )
    mapping = {
        ManagementRating.EXCELLENT: (
            "Evidence is consistent with high-quality capital allocation and "
            "financial discipline. Verify governance and incentive alignment "
            "with primary filings."
        ),
        ManagementRating.GOOD: (
            "Evidence supports generally sound management behaviour. Stress-test "
            "capital allocation and leverage across cycles."
        ),
        ManagementRating.AVERAGE: (
            "Evidence suggests average management quality. Focus diligence on "
            "capital allocation mistakes and accounting exceptions."
        ),
        ManagementRating.BELOW_AVERAGE: (
            "Evidence points to below-average management proxies. Demand a "
            "higher margin of safety and deeper primary-source review."
        ),
        ManagementRating.POOR: (
            "Evidence does not support high management quality. Avoid assuming "
            "rational capital allocation or conservative financing."
        ),
    }
    return mapping[rating]


def build_management_explainability(
    metadata: ManagementMetadata,
    components: tuple[ManagementComponentScore, ...],
    confidence: ManagementConfidence,
    rating: ManagementRating,
    score: float | None,
) -> ManagementExplainability:
    evidence: list[ManagementEvidence] = []
    for component in components:
        evidence.extend(component.evidence)
    assumptions = (
        "FinancialAnalysis and BusinessQualityAnalysis are accepted public inputs.",
        "Dimension scores are deterministic functions of documented proxies.",
        f"Framework version: {metadata.framework_version}.",
        "Buffett/Munger alignment: rational capital allocation, honesty, "
        "conservative financing, high returns on capital.",
    )
    limitations = (
        "No board independence, promoter ownership, RPT, or auditor feeds.",
        "Governance dimension is intentionally confidence- and score-capped.",
        "Guidance reliability and regulatory actions deferred.",
        "Does not forecast prices or issue buy/sell advice.",
        "Future AI-assisted analysis may enrich evidence without changing contracts.",
    )
    return ManagementExplainability(
        evidence=tuple(evidence),
        confidence=confidence,
        assumptions=assumptions,
        limitations=limitations,
        reasoning=build_summary(rating, score, components),
    )


def aggregate_factors(
    components: tuple[ManagementComponentScore, ...],
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
    components: tuple[ManagementComponentScore, ...],
) -> ManagementConfidence:
    values = [c.confidence.value for c in components if c.score.value is not None]
    if not values:
        return ManagementConfidence(value=0.0, basis="insufficient_component_scores")
    mean = sum(values) / len(values)
    return ManagementConfidence(
        value=round(mean, 4),
        basis="mean_component_confidence",
    )


def explain_from_analysis(analysis: ManagementAnalysis) -> ManagementExplainability:
    return analysis.explainability
