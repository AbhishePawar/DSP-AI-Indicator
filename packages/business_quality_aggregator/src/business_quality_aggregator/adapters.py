"""Adapters that read ONLY public analysis surfaces from domain engines."""

from __future__ import annotations

from typing import Any

from business_quality_aggregator.models import (
    AggregatorComponentResult,
    BusinessQualityAggregatorConfidence,
    BusinessQualityAggregatorEvidence,
    BusinessQualityAggregatorScore,
)
from business_quality_aggregator.scoring import AggregatorComponent

__all__ = [
    "component_score_01",
    "extract_component_result",
    "rating_value",
    "safe_score_value",
]


def safe_score_value(analysis: object | None) -> float | None:
    if analysis is None:
        return None
    score = getattr(analysis, "score", None)
    if score is None:
        return None
    value = getattr(score, "value", None)
    if value is None:
        return None
    return float(value)


def rating_value(analysis: object | None, attr: str) -> str | None:
    if analysis is None:
        return None
    rating = getattr(analysis, attr, None)
    if rating is None:
        return None
    value = getattr(rating, "value", rating)
    return str(value) if value is not None else None


def component_score_01(analysis: object | None, dimension: str) -> float | None:
    """Read a public component score (0–100) and normalise to 0–1."""
    if analysis is None:
        return None
    components = getattr(analysis, "components", ()) or ()
    for item in components:
        dim = getattr(item, "dimension", None)
        dim_value = getattr(dim, "value", dim)
        if str(dim_value) != dimension:
            continue
        score = getattr(item, "score", None)
        value = getattr(score, "value", None) if score is not None else None
        if value is None:
            return None
        return max(0.0, min(1.0, float(value) / 100.0))
    return None


def _confidence(analysis: object | None) -> BusinessQualityAggregatorConfidence:
    if analysis is None:
        return BusinessQualityAggregatorConfidence(
            value=0.0, basis="missing_engine_output"
        )
    conf = getattr(analysis, "confidence", None)
    if conf is None:
        return BusinessQualityAggregatorConfidence(
            value=0.35, basis="engine_confidence_absent"
        )
    value = float(getattr(conf, "value", 0.0) or 0.0)
    basis = str(getattr(conf, "basis", "engine_confidence") or "engine_confidence")
    return BusinessQualityAggregatorConfidence(value=value, basis=basis)


def _factors(analysis: object | None, *attrs: str) -> tuple[str, ...]:
    if analysis is None:
        return ()
    for attr in attrs:
        value = getattr(analysis, attr, None)
        if value:
            return tuple(str(item) for item in value)
    return ()


def _top_evidence(
    analysis: object | None, *, engine: str, limit: int = 3
) -> tuple[BusinessQualityAggregatorEvidence, ...]:
    if analysis is None:
        return ()
    items = getattr(analysis, "evidence", ()) or ()
    out: list[BusinessQualityAggregatorEvidence] = []
    for item in items[:limit]:
        out.append(
            BusinessQualityAggregatorEvidence(
                source=str(getattr(item, "source", engine)),
                reference=str(getattr(item, "reference", "analysis")),
                summary=str(getattr(item, "summary", "")),
                reasoning=str(getattr(item, "reasoning", "")),
                confidence=float(getattr(item, "confidence", 0.0) or 0.0),
                supporting_metrics=tuple(
                    str(m) for m in (getattr(item, "supporting_metrics", ()) or ())
                ),
                limitations=tuple(
                    str(m) for m in (getattr(item, "limitations", ()) or ())
                ),
                contributing_engines=(engine,),
            )
        )
    return tuple(out)


def extract_component_result(
    *,
    component: AggregatorComponent,
    analysis: object | None,
    weight: float,
    rating_attr: str,
) -> AggregatorComponentResult:
    score_value = safe_score_value(analysis)
    data_available = analysis is not None and score_value is not None
    engine_score = (
        BusinessQualityAggregatorScore(value=None, status="insufficient_data")
        if score_value is None
        else BusinessQualityAggregatorScore(value=round(score_value, 4), status="assessed")
    )
    contribution = None if score_value is None else round(score_value * weight, 4)
    return AggregatorComponentResult(
        component=component,
        engine_score=engine_score,
        engine_rating=rating_value(analysis, rating_attr),
        engine_confidence=_confidence(analysis),
        weight=weight,
        weighted_contribution=contribution,
        evidence=_top_evidence(analysis, engine=component.value),
        strengths=_factors(analysis, "strengths", "positive_factors"),
        weaknesses=_factors(analysis, "weaknesses", "negative_factors"),
        risks=_factors(analysis, "risks"),
        data_available=data_available,
    )


def analysis_bundle_metrics(analyses: dict[str, Any]) -> dict[str, float | None]:
    return {name: safe_score_value(obj) for name, obj in analyses.items()}
