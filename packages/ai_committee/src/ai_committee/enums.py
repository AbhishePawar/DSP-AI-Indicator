"""Committee-local enumerations.

These live in ``ai_committee`` (not ``contracts``) because Sprint 5.0
introduces a four-way decision vocabulary — BUY / HOLD / SELL /
NEUTRAL — that is deliberately distinct from
``contracts.RecommendationAction`` (which has STRONG_BUY / STRONG_SELL
and no NEUTRAL) and from ``contracts.SignalDirection`` (which is an
analytical bias, not an investment decision).
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["Decision"]


class Decision(StrEnum):
    """Discrete investment decision used by opinions and the committee.

    Member opinions use BUY / HOLD / SELL only. The committee's final
    :class:`~ai_committee.models.InvestmentDecision` may also be
    :attr:`NEUTRAL` when members conflict (BUY vs SELL).
    """

    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    NEUTRAL = "neutral"
