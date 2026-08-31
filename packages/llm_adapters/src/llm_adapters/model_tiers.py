"""Model tier definitions — provider-neutral, configurable.

Tiers are routing slots, not provider commitments. The default mapping
puts DeepSeek/Gemini on COST_EFFICIENT and OpenAI/Anthropic on PREMIUM,
but every entry is overridable via configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ModelTier(str, Enum):
    COST_EFFICIENT = "cost_efficient"
    PREMIUM = "premium"


@dataclass(frozen=True, slots=True)
class TierConfig:
    """Configurable per-tier model identity and quality floor."""

    tier: ModelTier
    model_identity: str
    min_quality_score: float
    description: str = ""


# Default mapping — overridable via ``tier_registry`` parameter.
# DeepSeek-chat and Gemini-1.5-Flash: COST_EFFICIENT.
# OpenAI gpt-4o-mini and Anthropic claude-3-5-sonnet: PREMIUM.
# Floors are explicit gates (not picked from thin air):
#   COST_EFFICIENT must clear 60/100 quality to pass.
#   PREMIUM must clear 80/100 quality to pass.
DEFAULT_TIERS: Mapping[ModelTier, TierConfig] = {
    ModelTier.COST_EFFICIENT: TierConfig(
        tier=ModelTier.COST_EFFICIENT,
        model_identity="deepseek:deepseek-chat",
        min_quality_score=60.0,
        description="Cheapest viable model for routine research.",
    ),
    ModelTier.PREMIUM: TierConfig(
        tier=ModelTier.PREMIUM,
        model_identity="anthropic:claude-3-5-sonnet-20241022",
        min_quality_score=80.0,
        description="Stronger model for escalated / high-complexity research.",
    ),
}


def get_tier_config(
    tier: ModelTier,
    registry: Mapping[ModelTier, TierConfig] | None = None,
) -> TierConfig:
    """Resolve a tier to its TierConfig, else raise KeyError."""
    src = registry if registry is not None else DEFAULT_TIERS
    if tier not in src:
        raise KeyError(f"Unknown tier: {tier!r}")
    return src[tier]


__all__ = [
    "DEFAULT_TIERS",
    "ModelTier",
    "TierConfig",
    "get_tier_config",
]
