"""Cost + composite scoring for evaluation results.

Deterministic and auditable:
    overall_score = 0.5 * quality_score + 0.5 * cost_score

Both sub-scores are 0-100. Cost scoring is relative across the supplied
set of results (cheapest = 100, most expensive = 0). Quality scoring
averages the non-None components of QualityEvaluation, scaled to 0-100.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from llm_adapters.evaluation import EvaluationResult, QualityEvaluation
from llm_adapters.model_catalog import ModelInfo, ModelPricing


def calculate_estimated_cost(usage, pricing: ModelPricing) -> float:
    """USD cost for a single run.

    Missing pricing -> returns 0.0 (caller must surface ``error_category``
    separately; this function does not invent numbers).
    """
    if pricing is None:
        return 0.0
    if usage.input_tokens < 0 or usage.output_tokens < 0:
        raise ValueError("token usage must be non-negative")
    cost = (usage.input_tokens / 1_000_000.0) * pricing.input_usd_per_1m
    cost += (usage.output_tokens / 1_000_000.0) * pricing.output_usd_per_1m
    # Round to 6 decimals — never display sub-cent precision as truth.
    return round(cost, 6)


def calculate_quality_score(quality: QualityEvaluation) -> float:
    """0-100 from non-None quality components (deterministic mean)."""
    components = quality.component_values()
    if not components:
        return 0.0
    for v in components:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"quality component out of [0,1]: {v!r}")
    return round(100.0 * (sum(components) / len(components)), 4)


def calculate_cost_score(
    results: Sequence[EvaluationResult],
    target: EvaluationResult,
) -> float:
    """0-100 relative cost score across the supplied result set.

    Cheapest successful result -> 100. Most expensive -> 0. If all costs
    are equal (or only one result), return 100. Failed results are
    included in the denominator for honesty — they still cost something.
    """
    costs = [r.estimated_cost_usd for r in results if r.estimated_cost_usd >= 0]
    if not costs or target.estimated_cost_usd <= 0:
        return 0.0
    cmin, cmax = min(costs), max(costs)
    if cmax == cmin:
        return 100.0
    # Cheaper is better: invert.
    score = 100.0 * (1.0 - (target.estimated_cost_usd - cmin) / (cmax - cmin))
    return round(max(0.0, min(100.0, score)), 4)


def calculate_overall_score(quality_score: float, cost_score: float) -> float:
    """50/50 weighted composite, 0-100."""
    for v in (quality_score, cost_score):
        if v < 0.0 or v > 100.0:
            raise ValueError(f"score out of [0,100]: {v!r}")
    return round(0.5 * quality_score + 0.5 * cost_score, 4)


@dataclass(frozen=True, slots=True)
class ScoredEvaluation:
    """EvaluationResult with computed sub-scores and composite."""

    result: EvaluationResult
    quality_score: float
    cost_score: float
    overall_score: float

    @property
    def model(self) -> ModelInfo:
        return self.result.model


def score_evaluations(results: Iterable[EvaluationResult]) -> list[ScoredEvaluation]:
    """Apply quality + cost + overall scoring to each result."""
    materialized = list(results)
    if not materialized:
        return []
    scored: list[ScoredEvaluation] = []
    for r in materialized:
        q = calculate_quality_score(r.quality)
        c = calculate_cost_score(materialized, r)
        o = calculate_overall_score(q, c)
        scored.append(ScoredEvaluation(result=r, quality_score=q, cost_score=c, overall_score=o))
    scored.sort(key=lambda s: s.overall_score, reverse=True)
    return scored


__all__ = [
    "ScoredEvaluation",
    "calculate_cost_score",
    "calculate_estimated_cost",
    "calculate_overall_score",
    "calculate_quality_score",
    "score_evaluations",
]
