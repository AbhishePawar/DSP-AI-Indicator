"""Aggregate analyzer signals into condition + recommendation.

Deterministic Sprint 6.0 rules (no probabilities, no forecasting):

* High GDP + Low Inflation + Stable/Accommodative Rates → BUY / EXPANSION
  or RECOVERY (depending on bullish breadth)
* High Inflation + Rapid Rate Hikes → SELL / CONTRACTION or SLOWING
* Mixed signals → HOLD / SLOWING
"""

from __future__ import annotations

from collections.abc import Sequence

from contracts.enums import SignalDirection

from economic.enums import EconomicCondition, Recommendation
from economic.models import EconomicSignal

__all__ = ["aggregate_signals"]


def aggregate_signals(
    signals: Sequence[EconomicSignal],
) -> tuple[EconomicCondition, Recommendation, str]:
    """Collapse detected signals into condition, recommendation, reasoning.

    Args:
        signals: All signals produced by the analyzers that ran.

    Returns:
        ``(overall_condition, recommendation, reasoning)``.

    Raises:
        ValueError: If ``signals`` is empty.
    """
    if not signals:
        msg = "signals must not be empty"
        raise ValueError(msg)

    bullish = sum(
        1 for s in signals if s.direction is SignalDirection.BULLISH
    )
    bearish = sum(
        1 for s in signals if s.direction is SignalDirection.BEARISH
    )
    neutral = len(signals) - bullish - bearish
    observations = ", ".join(s.observation for s in signals)

    if bullish > bearish:
        recommendation = Recommendation.BUY
        if bullish >= 3:
            condition = EconomicCondition.EXPANSION
            label = "broadly bullish"
        else:
            condition = EconomicCondition.RECOVERY
            label = "mildly bullish"
        reasoning = (
            f"Macro signals are {label} "
            f"({bullish} bullish, {bearish} bearish, {neutral} neutral): "
            f"{observations}. Recommendation is {recommendation.value}."
        )
        return condition, recommendation, reasoning

    if bearish > bullish:
        recommendation = Recommendation.SELL
        if bearish >= 3:
            condition = EconomicCondition.CONTRACTION
            label = "broadly bearish"
        else:
            condition = EconomicCondition.SLOWING
            label = "mildly bearish"
        reasoning = (
            f"Macro signals are {label} "
            f"({bullish} bullish, {bearish} bearish, {neutral} neutral): "
            f"{observations}. Recommendation is {recommendation.value}."
        )
        return condition, recommendation, reasoning

    recommendation = Recommendation.HOLD
    condition = EconomicCondition.SLOWING
    reasoning = (
        f"Macro signals are mixed "
        f"({bullish} bullish, {bearish} bearish, {neutral} neutral): "
        f"{observations}. Recommendation is {recommendation.value}."
    )
    return condition, recommendation, reasoning
