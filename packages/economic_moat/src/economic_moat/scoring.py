"""Scoring primitives and moat rating framework for Economic Moat Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from economic_moat.exceptions import EconomicMoatValidationError

__all__ = [
    "DEFAULT_MOAT_WEIGHTS",
    "MoatDimension",
    "MoatRating",
    "MoatWeights",
    "clip_score",
    "moat_rating_from_score",
    "validate_weights",
    "weighted_mean",
]


class MoatDimension(str, Enum):
    """Canonical Economic Moat analysis dimensions (Buffett-aligned)."""

    BRAND = "brand"
    NETWORK_EFFECTS = "network_effects"
    SWITCHING_COSTS = "switching_costs"
    COST_ADVANTAGE = "cost_advantage"
    INTANGIBLE_ASSETS = "intangible_assets"
    EFFICIENT_SCALE = "efficient_scale"


class MoatRating(str, Enum):
    """Ordinal overall moat rating — durability of competitive advantage."""

    NO_MOAT = "no_moat"
    WEAK = "weak"
    NARROW = "narrow"
    STRONG = "strong"
    WIDE = "wide"


@dataclass(frozen=True, slots=True)
class MoatWeights:
    """Normalized weights for overall moat score composition."""

    brand: float = 0.20
    network_effects: float = 0.15
    switching_costs: float = 0.20
    cost_advantage: float = 0.15
    intangible_assets: float = 0.15
    efficient_scale: float = 0.15

    def as_dict(self) -> dict[str, float]:
        return {
            MoatDimension.BRAND.value: self.brand,
            MoatDimension.NETWORK_EFFECTS.value: self.network_effects,
            MoatDimension.SWITCHING_COSTS.value: self.switching_costs,
            MoatDimension.COST_ADVANTAGE.value: self.cost_advantage,
            MoatDimension.INTANGIBLE_ASSETS.value: self.intangible_assets,
            MoatDimension.EFFICIENT_SCALE.value: self.efficient_scale,
        }

    def weight_for(self, dimension: MoatDimension) -> float:
        return self.as_dict()[dimension.value]

    def to_dict(self) -> dict[str, Any]:
        return self.as_dict()


DEFAULT_MOAT_WEIGHTS = MoatWeights()


def clip_score(value: float, *, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a numeric score into ``[lo, hi]``."""
    return max(lo, min(hi, value))


def weighted_mean(items: Sequence[tuple[float, float]]) -> float | None:
    """Return weighted mean of ``(value, weight)`` pairs; ``None`` if empty."""
    total_w = 0.0
    acc = 0.0
    for value, weight in items:
        if weight <= 0:
            continue
        total_w += weight
        acc += value * weight
    if total_w <= 0:
        return None
    return acc / total_w


def moat_rating_from_score(score: float | None) -> MoatRating:
    """Map a 0–100 overall moat score to an ordinal Buffett-style rating."""
    if score is None:
        return MoatRating.NO_MOAT
    if score >= 80.0:
        return MoatRating.WIDE
    if score >= 65.0:
        return MoatRating.STRONG
    if score >= 45.0:
        return MoatRating.NARROW
    if score >= 25.0:
        return MoatRating.WEAK
    return MoatRating.NO_MOAT


def validate_weights(weights: MoatWeights | Mapping[str, float] | None) -> MoatWeights:
    """Validate and normalize moat weights (must be finite and sum ≈ 1.0)."""
    if weights is None:
        return DEFAULT_MOAT_WEIGHTS
    if isinstance(weights, MoatWeights):
        payload = weights.as_dict()
    else:
        payload = {str(k): float(v) for k, v in weights.items()}
    required = {d.value for d in MoatDimension}
    missing = required - set(payload)
    if missing:
        raise EconomicMoatValidationError(
            f"Missing moat weight keys: {sorted(missing)}"
        )
    values = [float(payload[k]) for k in sorted(required)]
    if any(not (v == v) or v < 0 for v in values):  # NaN / negative
        raise EconomicMoatValidationError("Moat weights must be finite and >= 0")
    total = sum(values)
    if abs(total - 1.0) > 1e-6:
        raise EconomicMoatValidationError(
            f"Moat weights must sum to 1.0 (got {total})"
        )
    return MoatWeights(
        brand=float(payload[MoatDimension.BRAND.value]),
        network_effects=float(payload[MoatDimension.NETWORK_EFFECTS.value]),
        switching_costs=float(payload[MoatDimension.SWITCHING_COSTS.value]),
        cost_advantage=float(payload[MoatDimension.COST_ADVANTAGE.value]),
        intangible_assets=float(payload[MoatDimension.INTANGIBLE_ASSETS.value]),
        efficient_scale=float(payload[MoatDimension.EFFICIENT_SCALE.value]),
    )
