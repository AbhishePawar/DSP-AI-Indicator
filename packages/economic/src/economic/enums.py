"""Economic Engine enumerations.

These live in ``economic`` (not ``contracts``) because they are
engine-local vocabulary for this sprint's deterministic macro rules.
A future sprint may promote shared shapes into Contracts once Valuation
and the AI Investment Committee consume them cross-engine.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["EconomicCondition", "Recommendation"]


class EconomicCondition(StrEnum):
    """Overall macroeconomic regime classification."""

    EXPANSION = "expansion"
    SLOWING = "slowing"
    CONTRACTION = "contraction"
    RECOVERY = "recovery"


class Recommendation(StrEnum):
    """Deterministic macro-stance recommendation for this sprint.

    Distinct from ``contracts.RecommendationAction`` (which includes
    STRONG_BUY / STRONG_SELL and is the AI Investment Committee's
    terminal vocabulary). This enum is BUY / HOLD / SELL only.
    """

    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
