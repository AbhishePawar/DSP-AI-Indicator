"""Explainability builders for Economic Moat Intelligence."""

from __future__ import annotations

from economic_moat.metadata import EconomicMetadata
from economic_moat.models import (
    EconomicAnalysis,
    EconomicConfidence,
    EconomicEvidence,
    EconomicExplainability,
    MoatComponentScore,
)
from economic_moat.scoring import MoatRating

__all__ = [
    "ECONOMIC_MOAT_RESEARCH_DISCLAIMER",
    "build_moat_explainability",
    "build_recommendation",
    "build_summary",
]

ECONOMIC_MOAT_RESEARCH_DISCLAIMER = (
    "Economic Moat Intelligence provides research-only, evidence-backed "
    "assessments of competitive advantage durability. It is not investment "
    "advice, a buy/sell recommendation, or a guarantee of future returns. "
    "Scores are rule-based proxies derived from FinancialAnalysis and "
    "BusinessQualityAnalysis; opaque or unverifiable claims are avoided."
)


def build_summary(
    rating: MoatRating,
    score: float | None,
    components: tuple[MoatComponentScore, ...],
) -> str:
    """Deterministic one-paragraph research summary."""
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
        f"Overall economic moat rating is {rating.value} "
        f"(score {score_txt}) based on six Buffett-aligned dimensions."
        f"{strong_txt}{weak_txt} "
        "Interpretation emphasizes durability and capital efficiency over "
        "short-term sentiment."
    )


def build_recommendation(rating: MoatRating, confidence: EconomicConfidence) -> str:
    """Research framing — not a securities recommendation."""
    if confidence.value < 0.35:
        return (
            "Insufficient evidence confidence for a durable-moat conclusion; "
            "treat scores as provisional research hypotheses only."
        )
    mapping = {
        MoatRating.WIDE: (
            "Evidence is consistent with a wide, durable competitive advantage. "
            "Prioritize verifying longevity of pricing power and capital returns."
        ),
        MoatRating.STRONG: (
            "Evidence supports a strong moat hypothesis. Stress-test switching "
            "costs and cost advantages across cycles."
        ),
        MoatRating.NARROW: (
            "Evidence suggests a narrow moat. Focus on whether advantages are "
            "eroding or expanding over multi-year horizons."
        ),
        MoatRating.WEAK: (
            "Evidence points to a weak moat. Competitive position may be "
            "contestable; demand higher margin of safety in research."
        ),
        MoatRating.NO_MOAT: (
            "Evidence does not support a meaningful economic moat. "
            "Avoid assuming durable competitive advantage."
        ),
    }
    return mapping[rating]


def build_moat_explainability(
    metadata: EconomicMetadata,
    components: tuple[MoatComponentScore, ...],
    confidence: EconomicConfidence,
    rating: MoatRating,
    score: float | None,
) -> EconomicExplainability:
    """Compose package-level explainability from component evidence."""
    evidence: list[EconomicEvidence] = []
    for component in components:
        evidence.extend(component.evidence)
    assumptions = (
        "FinancialAnalysis and BusinessQualityAnalysis are accepted public inputs.",
        "Dimension scores are deterministic functions of documented proxies.",
        f"Framework version: {metadata.framework_version}.",
        "Buffett alignment: durability, predictability, competitive advantage, "
        "capital efficiency — not short-term market sentiment.",
    )
    limitations = (
        "No peer comparisons, industry HHI, brand surveys, or patent registries.",
        "Network effects and efficient scale are intentionally confidence-capped.",
        "Does not forecast prices or issue buy/sell advice.",
        "Future AI-assisted analysis may enrich evidence without changing contracts.",
    )
    reasoning = build_summary(rating, score, components)
    return EconomicExplainability(
        evidence=tuple(evidence),
        confidence=confidence,
        assumptions=assumptions,
        limitations=limitations,
        reasoning=reasoning,
    )


def aggregate_factors(
    components: tuple[MoatComponentScore, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Flatten positive/negative/risk factors across components."""
    positives: list[str] = []
    negatives: list[str] = []
    risks: list[str] = []
    for component in components:
        positives.extend(component.positive_factors)
        negatives.extend(component.negative_factors)
        risks.extend(component.risks)
    return tuple(positives), tuple(negatives), tuple(risks)


def analysis_confidence(
    components: tuple[MoatComponentScore, ...],
) -> EconomicConfidence:
    """Mean component confidence; insufficient if no assessed scores."""
    values = [c.confidence.value for c in components if c.score.value is not None]
    if not values:
        return EconomicConfidence(value=0.0, basis="insufficient_component_scores")
    mean = sum(values) / len(values)
    return EconomicConfidence(
        value=round(mean, 4),
        basis="mean_component_confidence",
    )


# Re-export helper used by engine without circular imports in tests
def explain_from_analysis(analysis: EconomicAnalysis) -> EconomicExplainability:
    return analysis.explainability
