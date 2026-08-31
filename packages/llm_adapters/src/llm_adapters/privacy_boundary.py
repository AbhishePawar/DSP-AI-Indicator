"""Privacy boundary — Private internal result vs Public decision pack.

The public schema is a strict superset of fields, never a superset of
sources. Private fields are physically separate (not just hidden) so
accidental ``**kwargs`` unpacking cannot leak them.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


# Names that must NEVER appear in the public pack.
_PRIVATE_FIELD_NAMES: frozenset[str] = frozenset(
    {
        "provider",
        "model",
        "routing_tier",
        "routing_reasons",
        "confidence_requirement",
        "estimated_cost_usd",
        "input_tokens",
        "output_tokens",
        "latency_ms",
        "model_score",
        "routing_criteria",
        "internal_prompt",
        "tool_calls",
        "tool_results",
        "raw_ai_response",
        "internal_validation",
        "chain_of_thought",
    }
)


@dataclass(frozen=True, slots=True)
class PublicDecisionPack:
    """Client-facing approved research result.

    Schema is intentionally narrow: it makes accidental serialization
    of private fields impossible because they are not declared here.
    """

    recommendation: str
    valuation: str | None
    analysis: str
    risks: tuple[str, ...]
    evidence_citations: tuple[str, ...]
    confidence: float
    limitations: tuple[str, ...]
    schema_version: str = "public_decision_pack_v1"

    def to_dict(self) -> dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass(frozen=True, slots=True)
class PrivateInternalResult:
    """Server-side private artifact.

    Carries everything that must never reach the browser: provider,
    model, tier, cost, tokens, internal prompt, tool calls, raw AI
    response, internal validation, chain-of-thought.
    """

    public: PublicDecisionPack
    provider: str
    model: str
    routing_tier: str
    routing_reasons: tuple[str, ...]
    confidence_requirement: float
    estimated_cost_usd: float
    input_tokens: int
    output_tokens: int
    latency_ms: int
    model_score: float
    routing_criteria: tuple[str, ...]
    internal_prompt: str
    tool_calls: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    tool_results: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    raw_ai_response: str = ""
    internal_validation: dict[str, Any] = field(default_factory=dict)
    chain_of_thought: str = ""
    audit: dict[str, Any] = field(default_factory=dict)

    def to_public(self) -> PublicDecisionPack:
        """Return only the public pack. Refuses to include private fields."""
        return self.public


def assert_no_private_leakage(pack_dict: dict[str, Any]) -> None:
    """Test/runtime guard: reject any dict containing private field names."""
    leaked = sorted(set(pack_dict.keys()) & _PRIVATE_FIELD_NAMES)
    if leaked:
        raise ValueError(f"private fields leaked into public pack: {leaked}")


__all__ = [
    "PrivateInternalResult",
    "PublicDecisionPack",
    "assert_no_private_leakage",
]
