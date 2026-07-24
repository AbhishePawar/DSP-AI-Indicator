"""Deterministic voting and signal-collapse helpers.

Sprint 6.1 equal-weight voting (no AI, no weights, no probabilities):

* Clear plurality wins (e.g. BUY BUY HOLD → BUY, BUY BUY SELL → BUY).
* BUY/SELL/HOLD three-way split → NEUTRAL.
* BUY tied with SELL (any HOLD count below or equal) → NEUTRAL.
* BUY tied with HOLD and no leading SELL → HOLD (conservative;
  preserves Sprint 5.0 two-member BUY+HOLD → HOLD).
* SELL tied with HOLD and no leading BUY → HOLD.

Member-level collapse maps engine ``SignalDirection`` values onto
BUY / HOLD / SELL before the committee aggregates.
"""

from __future__ import annotations

from collections.abc import Sequence

from contracts.domain.signal import Signal
from contracts.enums import SignalDirection

from ai_committee.enums import Decision

__all__ = [
    "aggregate_recommendations",
    "collapse_signals",
    "signal_direction_to_decision",
]


def signal_direction_to_decision(direction: SignalDirection) -> Decision:
    """Map a ``contracts.SignalDirection`` onto a member :class:`Decision`.

    Args:
        direction: Analytical bias from an upstream engine signal.

    Returns:
        BUY for bullish, SELL for bearish, HOLD for neutral.
    """
    if direction is SignalDirection.BULLISH:
        return Decision.BUY
    if direction is SignalDirection.BEARISH:
        return Decision.SELL
    return Decision.HOLD


def collapse_signals(signals: Sequence[Signal]) -> Decision:
    """Collapse many engine signals into one member recommendation.

    Counts bullish versus bearish readings. Neutral readings do not tip
    either side. The side with the strictly greater count wins; a tie
    (including an empty or all-neutral set) is HOLD.

    Args:
        signals: Directional readings from one upstream engine.

    Returns:
        A member-level :class:`Decision` (BUY / HOLD / SELL).
    """
    bullish = sum(
        1 for s in signals if s.direction is SignalDirection.BULLISH
    )
    bearish = sum(
        1 for s in signals if s.direction is SignalDirection.BEARISH
    )
    if bullish > bearish:
        return Decision.BUY
    if bearish > bullish:
        return Decision.SELL
    return Decision.HOLD


def aggregate_recommendations(
    recommendations: Sequence[Decision],
) -> Decision:
    """Aggregate member recommendations via equal-weight plurality.

    Args:
        recommendations: One BUY / HOLD / SELL per voting member.
            NEUTRAL is not a valid member recommendation.

    Returns:
        The committee-level :class:`Decision`, which may be NEUTRAL
        when BUY and SELL tie for the lead.

    Raises:
        ValueError: If ``recommendations`` is empty or contains
            NEUTRAL.
    """
    if not recommendations:
        msg = "recommendations must not be empty"
        raise ValueError(msg)
    if any(r is Decision.NEUTRAL for r in recommendations):
        msg = "member recommendations must not include NEUTRAL"
        raise ValueError(msg)

    buy = sum(1 for r in recommendations if r is Decision.BUY)
    hold = sum(1 for r in recommendations if r is Decision.HOLD)
    sell = sum(1 for r in recommendations if r is Decision.SELL)

    tallies = (
        (Decision.BUY, buy),
        (Decision.HOLD, hold),
        (Decision.SELL, sell),
    )
    top_count = max(buy, hold, sell)
    leaders = tuple(decision for decision, count in tallies if count == top_count)

    if len(leaders) == 1:
        return leaders[0]

    # Tie for the lead.
    if Decision.BUY in leaders and Decision.SELL in leaders:
        return Decision.NEUTRAL
    if Decision.HOLD in leaders:
        # BUY+HOLD or SELL+HOLD tie → HOLD (conservative / Sprint 5.0).
        return Decision.HOLD
    return Decision.NEUTRAL
