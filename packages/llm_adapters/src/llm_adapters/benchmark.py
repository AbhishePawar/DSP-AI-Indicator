"""Offline benchmark — compare models on identical research cases.

Rules:
- identical research_case_id, research_spec_version, evidence reference
- identical output schema
- unknown pricing is recorded as a cost anomaly, not treated as 0
- benchmark score = 0.5*quality + 0.5*cost_efficiency
- minimum quality gate overrides cost ranking
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

from llm_adapters.cost_scoring import (
    calculate_cost_score,
    calculate_quality_score,
)
from llm_adapters.evaluation import (
    EvaluationResult,
    EvaluationStatus,
)
from llm_adapters.model_catalog import (
    DEFAULT_CATALOG,
    ModelInfo,
    ModelPricing,
    get_model_info,
)
from llm_adapters.model_tiers import (
    DEFAULT_TIERS,
    ModelTier,
    TierConfig,
    get_tier_config,
)
from llm_adapters.quality_gate import GateOutcome, evaluate_gate
from llm_adapters.routing import ComplexitySignal, decide_routing


@dataclass(frozen=True, slots=True)
class BenchmarkRow:
    """One row of the benchmark table for a (case, model) pair."""

    research_case_id: str
    model: ModelInfo
    tier: ModelTier
    quality_score: float
    cost_score: float
    benchmark_score: float
    meets_floor: bool
    gate_outcome: GateOutcome
    estimated_cost_usd: float
    latency_ms: int
    pricing_missing: bool


def _is_pricing_missing(pricing: ModelPricing | None) -> bool:
    if pricing is None:
        return True
    return pricing.input_usd_per_1m <= 0 and pricing.output_usd_per_1m <= 0


def _resolve_tier_for_model(
    model_identity: str,
    tier_registry: dict[ModelTier, TierConfig] | None = None,
) -> ModelTier:
    """Map a model identity to its tier via the tier registry.

    A model not registered as the tier-default is unassigned — defaults
    to COST_EFFICIENT (cheap path first).
    """
    src = tier_registry if tier_registry is not None else DEFAULT_TIERS
    for tier, cfg in src.items():
        if cfg.model_identity == model_identity:
            return tier
    return ModelTier.COST_EFFICIENT


def run_case_against_model(
    *,
    research_case_id: str,
    research_spec_version: str,
    model_identity: str,
    signals: Iterable[ComplexitySignal],
    run_model: Callable[[str, ModelTier], EvaluationResult],
    tier_registry: dict[ModelTier, TierConfig] | None = None,
    catalog: dict[str, ModelInfo] | None = None,
) -> BenchmarkRow:
    """Run one research case against one model under the gating policy."""
    decision = decide_routing(signals)
    # Route via DSP decision, not the model's preference.
    run_tier = decision.routing_tier
    result = run_model(model_identity, run_tier)

    info = get_model_info(model_identity, catalog)
    pricing_missing = _is_pricing_missing(info.pricing)
    if pricing_missing:
        # Flag but DO NOT silently treat as zero. Mark so benchmark surfaces it.
        effective_cost = float("nan")
    else:
        effective_cost = result.estimated_cost_usd

    verdict = evaluate_gate(
        result,
        decision,
        tier_registry=tier_registry,
    )
    quality_score = calculate_quality_score(result.quality)
    return BenchmarkRow(
        research_case_id=research_case_id,
        model=info,
        tier=run_tier,
        quality_score=quality_score,
        cost_score=0.0,  # filled by benchmark table
        benchmark_score=0.0,  # filled by benchmark table
        meets_floor=verdict.meets_floor,
        gate_outcome=verdict.outcome,
        estimated_cost_usd=effective_cost,
        latency_ms=result.latency_ms,
        pricing_missing=pricing_missing,
    )


def build_benchmark_table(
    rows: Sequence[BenchmarkRow],
) -> list[BenchmarkRow]:
    """Compute cost_score and benchmark_score across the row set.

    Unknown pricing rows are EXCLUDED from the cost denominator and
    flagged via ``pricing_missing=True``. They cannot win on benchmark.
    """
    costed = [r for r in rows if not r.pricing_missing and r.estimated_cost_usd == r.estimated_cost_usd]
    if not costed:
        return list(rows)

    costs = [r.estimated_cost_usd for r in costed]
    cmin, cmax = min(costs), max(costs)
    enriched: list[BenchmarkRow] = []
    for r in rows:
        if r.pricing_missing or r.estimated_cost_usd != r.estimated_cost_usd:
            cost_score = 0.0
            benchmark_score = 0.0
        elif cmax == cmin:
            cost_score = 100.0
            benchmark_score = 0.5 * r.quality_score + 0.5 * cost_score
        else:
            cost_score = max(
                0.0,
                min(
                    100.0,
                    100.0 * (1.0 - (r.estimated_cost_usd - cmin) / (cmax - cmin)),
                ),
            )
            benchmark_score = 0.5 * r.quality_score + 0.5 * cost_score
        # Apply minimum quality gate override.
        if not r.meets_floor:
            benchmark_score = 0.0
        enriched.append(
            BenchmarkRow(
                research_case_id=r.research_case_id,
                model=r.model,
                tier=r.tier,
                quality_score=r.quality_score,
                cost_score=cost_score,
                benchmark_score=benchmark_score,
                meets_floor=r.meets_floor,
                gate_outcome=r.gate_outcome,
                estimated_cost_usd=r.estimated_cost_usd,
                latency_ms=r.latency_ms,
                pricing_missing=r.pricing_missing,
            )
        )
    enriched.sort(key=lambda x: x.benchmark_score, reverse=True)
    return enriched


__all__ = [
    "BenchmarkRow",
    "build_benchmark_table",
    "run_case_against_model",
]
