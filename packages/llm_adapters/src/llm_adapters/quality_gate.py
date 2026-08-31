"""Quality gate + escalation policy.

A cheap model cannot pass simply because it is cheap. The gate enforces
a per-tier minimum quality_score, escalates COST_EFFICIENT -> PREMIUM on
validation failure, and fails closed (returns ``escalation_exhausted``)
if PREMIUM also fails. Never fabricates a recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from llm_adapters.cost_scoring import (
    calculate_quality_score,
)
from llm_adapters.evaluation import (
    ErrorCategory,
    EvaluationResult,
    EvaluationStatus,
)
from llm_adapters.model_tiers import (
    ModelTier,
    TierConfig,
    get_tier_config,
)
from llm_adapters.routing import RoutingDecision


class GateOutcome(str, Enum):
    ACCEPTED = "accepted"  # passed at current tier
    ESCALATED = "escalated"  # failed at COST_EFFICIENT, retry at PREMIUM
    FAILED_CLOSED = "failed_closed"  # failed at PREMIUM too — no fabrication


@dataclass(frozen=True, slots=True)
class GateVerdict:
    """Private internal verdict — never serialized to clients."""

    outcome: GateOutcome
    tier: ModelTier
    quality_score: float
    meets_floor: bool
    reason: str
    requires_escalation: bool


def _meets_floor(quality_score: float, tier: TierConfig) -> bool:
    return quality_score >= tier.min_quality_score


def evaluate_gate(
    result: EvaluationResult,
    decision: RoutingDecision,
    tier_registry: dict[ModelTier, TierConfig] | None = None,
) -> GateVerdict:
    """Apply per-tier quality floor + escalation policy.

    Rules:
    - status != SUCCESS or error_category != NONE -> requires escalation
    - quality below tier floor -> requires escalation
    - at PREMIUM, same conditions -> FAILED_CLOSED
    """
    tier_cfg = get_tier_config(decision.routing_tier, tier_registry)
    quality_score = calculate_quality_score(result.quality)
    meets = _meets_floor(quality_score, tier_cfg)

    # Operational failures always escalate (or fail closed at PREMIUM).
    op_failed = (
        result.status is not EvaluationStatus.SUCCESS
        or result.error_category not in (ErrorCategory.NONE,)
    )

    if not op_failed and meets:
        return GateVerdict(
            outcome=GateOutcome.ACCEPTED,
            tier=decision.routing_tier,
            quality_score=quality_score,
            meets_floor=True,
            reason="quality meets tier floor and no operational failure",
            requires_escalation=False,
        )

    # Build reason list.
    reasons: list[str] = []
    if op_failed:
        reasons.append(f"operational failure: {result.error_category.value}")
    if not meets:
        reasons.append(
            f"quality {quality_score:.2f} < floor {tier_cfg.min_quality_score:.2f}"
        )

    if decision.routing_tier is ModelTier.PREMIUM:
        return GateVerdict(
            outcome=GateOutcome.FAILED_CLOSED,
            tier=decision.routing_tier,
            quality_score=quality_score,
            meets_floor=meets,
            reason="; ".join(reasons) + " (premium also failed)",
            requires_escalation=False,
        )

    return GateVerdict(
        outcome=GateOutcome.ESCALATED,
        tier=decision.routing_tier,
        quality_score=quality_score,
        meets_floor=meets,
        reason="; ".join(reasons) + " -> escalate to premium",
        requires_escalation=True,
    )


def run_with_escalation(
    *,
    decision: RoutingDecision,
    run_at_tier: Callable[[ModelTier], EvaluationResult],
    tier_registry: dict[ModelTier, TierConfig] | None = None,
) -> tuple[GateVerdict, EvaluationResult | None]:
    """Run a tier, apply gate, escalate to PREMIUM if needed.

    Returns (verdict, accepted_result | None). On FAILED_CLOSED, the
    accepted_result is None — caller must NOT fabricate a recommendation.
    """
    current_tier = decision.routing_tier
    result = run_at_tier(current_tier)
    verdict = evaluate_gate(result, decision, tier_registry)

    if verdict.outcome is GateOutcome.ACCEPTED:
        return verdict, result

    if verdict.outcome is GateOutcome.ESCALATED:
        premium_decision = RoutingDecision(
            routing_tier=ModelTier.PREMIUM,
            routing_reasons=decision.routing_reasons,
            confidence_requirement=0.8,
        )
        premium_result = run_at_tier(ModelTier.PREMIUM)
        premium_verdict = evaluate_gate(premium_result, premium_decision, tier_registry)
        return premium_verdict, premium_result if premium_verdict.outcome is GateOutcome.ACCEPTED else None

    return verdict, None


__all__ = [
    "GateOutcome",
    "GateVerdict",
    "evaluate_gate",
    "run_with_escalation",
]
