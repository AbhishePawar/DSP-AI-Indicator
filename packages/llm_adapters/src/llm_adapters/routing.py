"""DSP routing policy — deterministic, AI must NOT decide its own tier.

Inputs: case complexity signals (deterministic facts produced by DSP).
Output: routing_tier, routing_reasons, confidence_requirement.

These outputs are PRIVATE. They never leave the server boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from llm_adapters.model_tiers import ModelTier


class ComplexitySignal(str, Enum):
    """Discrete signals that influence routing."""

    MISSING_DATA = "missing_data"
    INSUFFICIENT_HISTORY = "insufficient_history"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    VALUATION_DISAGREEMENT = "valuation_disagreement"
    HIGH_UNCERTAINTY = "high_uncertainty"
    UNUSUAL_FINANCIAL_STRUCTURE = "unusual_financial_structure"
    MATERIAL_RISK = "material_risk"
    DIFFICULT_BUFFETT_ANALYSIS = "difficult_buffett_analysis"
    TOOL_FAILURE = "tool_failure"
    VALIDATION_FAILURE = "validation_failure"
    HIGH_IMPACT_DECISION = "high_impact_decision"


# Escalation triggers: any of these forces PREMIUM.
_PREMIUM_TRIGGERS: frozenset[ComplexitySignal] = frozenset(
    {
        ComplexitySignal.CONFLICTING_EVIDENCE,
        ComplexitySignal.VALUATION_DISAGREEMENT,
        ComplexitySignal.UNUSUAL_FINANCIAL_STRUCTURE,
        ComplexitySignal.MATERIAL_RISK,
        ComplexitySignal.DIFFICULT_BUFFETT_ANALYSIS,
        ComplexitySignal.HIGH_IMPACT_DECISION,
    }
)

# Confidence requirements per tier.
_CONFIDENCE_REQUIREMENT: dict[ModelTier, float] = {
    ModelTier.COST_EFFICIENT: 0.6,
    ModelTier.PREMIUM: 0.8,
}


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    """Private internal routing decision — never serialized to clients."""

    routing_tier: ModelTier
    routing_reasons: tuple[str, ...]
    confidence_requirement: float

    def is_escalated(self) -> bool:
        return self.routing_tier is ModelTier.PREMIUM


def decide_routing(signals: Iterable[ComplexitySignal]) -> RoutingDecision:
    """Deterministic DSP routing — AI must NOT decide its own tier.

    Rules:
    - any PREMIUM_TRIGGER signal → PREMIUM
    - otherwise → COST_EFFICIENT
    - reasons list is sorted, deduplicated, deterministic
    """
    unique = sorted({s for s in signals}, key=lambda x: x.value)
    premium_reasons = [s.value for s in unique if s in _PREMIUM_TRIGGERS]
    tier = ModelTier.PREMIUM if premium_reasons else ModelTier.COST_EFFICIENT
    return RoutingDecision(
        routing_tier=tier,
        routing_reasons=tuple(premium_reasons),
        confidence_requirement=_CONFIDENCE_REQUIREMENT[tier],
    )


__all__ = [
    "ComplexitySignal",
    "RoutingDecision",
    "decide_routing",
]
