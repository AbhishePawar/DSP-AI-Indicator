"""Scoring primitives and decision scale for Investment Committee."""

from __future__ import annotations

from enum import Enum

from investment_committee.exceptions import InvestmentCommitteeValidationError

__all__ = [
    "CommitteeDecision",
    "ReviewerRole",
    "ACTION_RANK",
    "clip_score",
    "decision_from_score",
    "decision_from_rank",
    "rank_of",
]


class ReviewerRole(str, Enum):
    BUFFETT_ANALYST = "buffett_analyst"
    VALUE_INVESTOR = "value_investor"
    QUALITY_INVESTOR = "quality_investor"
    GROWTH_INVESTOR = "growth_investor"
    RISK_OFFICER = "risk_officer"


class CommitteeDecision(str, Enum):
    STRONG_SELL = "strong_sell"
    SELL = "sell"
    REDUCE = "reduce"
    HOLD = "hold"
    ACCUMULATE = "accumulate"
    BUY = "buy"
    STRONG_BUY = "strong_buy"


ACTION_RANK: dict[CommitteeDecision, int] = {
    CommitteeDecision.STRONG_SELL: 0,
    CommitteeDecision.SELL: 1,
    CommitteeDecision.REDUCE: 2,
    CommitteeDecision.HOLD: 3,
    CommitteeDecision.ACCUMULATE: 4,
    CommitteeDecision.BUY: 5,
    CommitteeDecision.STRONG_BUY: 6,
}


def clip_score(value: float, *, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def decision_from_score(score: float | None) -> CommitteeDecision:
    if score is None:
        return CommitteeDecision.HOLD
    if score >= 85.0:
        return CommitteeDecision.STRONG_BUY
    if score >= 75.0:
        return CommitteeDecision.BUY
    if score >= 65.0:
        return CommitteeDecision.ACCUMULATE
    if score >= 50.0:
        return CommitteeDecision.HOLD
    if score >= 40.0:
        return CommitteeDecision.REDUCE
    if score >= 25.0:
        return CommitteeDecision.SELL
    return CommitteeDecision.STRONG_SELL


def decision_from_rank(rank: float) -> CommitteeDecision:
    r = int(round(max(0.0, min(6.0, rank))))
    for decision, value in ACTION_RANK.items():
        if value == r:
            return decision
    return CommitteeDecision.HOLD


def rank_of(decision: CommitteeDecision | str | None) -> int:
    if decision is None:
        return ACTION_RANK[CommitteeDecision.HOLD]
    if isinstance(decision, CommitteeDecision):
        return ACTION_RANK[decision]
    try:
        return ACTION_RANK[CommitteeDecision(str(decision))]
    except ValueError as exc:
        raise InvestmentCommitteeValidationError(
            f"Unknown committee decision: {decision}"
        ) from exc
