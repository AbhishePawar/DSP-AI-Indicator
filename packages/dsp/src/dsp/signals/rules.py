"""Deterministic rules for interpreting an :class:`IndicatorResult`.

A "rule" is a pure function ``IndicatorResult -> RuleOutcome``: it looks
at what one indicator computed and decides a directional bias, a
human-readable reason, and (where meaningful) the threshold or reference
value that justified it. This is the single point where indicator-specific
meaning ("RSI above 70 is overbought", "price crossing above its moving
average is bullish") enters the platform — everything downstream
(:mod:`dsp.signals.signal_generator`,
:mod:`dsp.signals.explanation_generator`,
:mod:`dsp.signals.evidence_generator`) consumes the same
:class:`RuleOutcome` so a signal, its explanation, and its evidence can
never disagree with each other about *why* they exist.

Rules are registered by indicator name in a module-level
:class:`core.registry.Registry`, following the exact extension pattern
:mod:`dsp.registry` already established for indicators themselves —
adding a rule for a future indicator means registering a new callable,
never editing :class:`~dsp.signals.signal_generator.SignalGenerator`.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from contracts.enums import SignalDirection
from core.registry import Registry
from dsp.engine.models import IndicatorResult

RuleFn = Callable[[IndicatorResult], "RuleOutcome"]


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    """The result of evaluating one deterministic rule.

    Attributes:
        direction: Directional bias the rule concluded.
        reasoning: Human-readable sentence explaining the conclusion.
            Reused verbatim as the basis for the accompanying
            ``contracts.Explanation`` and ``contracts.Evidence``.
        threshold: The threshold or reference value the rule compared
            against, if any (e.g. the overbought level, or the moving
            average value price crossed).
        strength: Normalized confidence/magnitude in ``[0.0, 1.0]``, or
            ``None`` when the rule has no meaningful strength to report
            (e.g. a neutral reading).
    """

    direction: SignalDirection
    reasoning: str
    threshold: float | None = None
    strength: float | None = None


def _insufficient_data(result: IndicatorResult) -> RuleOutcome:
    """Return the shared "not enough data" outcome for any rule."""
    return RuleOutcome(
        direction=SignalDirection.NEUTRAL,
        reasoning=f"{result.label} has insufficient data to produce a reading.",
        threshold=None,
        strength=None,
    )


def evaluate_threshold_rule(
    result: IndicatorResult,
    *,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> RuleOutcome:
    """Evaluate a bounded-oscillator threshold rule (e.g. RSI).

    A reading above ``overbought`` is bearish (overbought conditions); a
    reading below ``oversold`` is bullish (oversold conditions); anything
    in between is neutral.

    Args:
        result: The indicator computation to interpret.
        overbought: Upper threshold, e.g. ``70.0`` for RSI.
        oversold: Lower threshold, e.g. ``30.0`` for RSI.

    Returns:
        The rule's directional conclusion and reasoning.
    """
    value = result.latest_value
    if math.isnan(value):
        return _insufficient_data(result)

    if value > overbought:
        span = 100.0 - overbought
        strength = min(1.0, (value - overbought) / span) if span > 0 else 1.0
        reasoning = (
            f"{result.label} is {value:.1f}, above the overbought threshold "
            f"of {overbought:.1f}, indicating overbought conditions."
        )
        return RuleOutcome(
            direction=SignalDirection.BEARISH,
            reasoning=reasoning,
            threshold=overbought,
            strength=strength,
        )

    if value < oversold:
        strength = min(1.0, (oversold - value) / oversold) if oversold > 0 else 1.0
        reasoning = (
            f"{result.label} is {value:.1f}, below the oversold threshold "
            f"of {oversold:.1f}, indicating oversold conditions."
        )
        return RuleOutcome(
            direction=SignalDirection.BULLISH,
            reasoning=reasoning,
            threshold=oversold,
            strength=strength,
        )

    reasoning = (
        f"{result.label} is {value:.1f}, within the neutral range "
        f"[{oversold:.1f}, {overbought:.1f}]."
    )
    return RuleOutcome(
        direction=SignalDirection.NEUTRAL,
        reasoning=reasoning,
        threshold=None,
        strength=None,
    )


def evaluate_crossover_rule(result: IndicatorResult) -> RuleOutcome:
    """Evaluate a price-versus-moving-average crossover rule.

    Applies to any moving-average-style indicator (SMA, EMA, WMA): a
    bullish crossover is close price moving from at-or-below the moving
    average to strictly above it between the previous and latest bar; a
    bearish crossover is the mirror case. No crossover on the latest bar
    is neutral, even if price is simply above or below the average without
    having just crossed it — this deliberately reports crossover *events*,
    not standing position, matching the mission's literal "EMA crossover"
    framing rather than a broader "price is above its average" bias.

    Args:
        result: The indicator computation to interpret. ``result.values``
            is the moving average line; ``result.source_values`` is the
            close prices it was computed from.

    Returns:
        The rule's directional conclusion and reasoning.
    """
    values = result.values
    source = result.source_values
    if len(values) < 2 or len(source) < 2:
        return _insufficient_data(result)

    prev_ma, curr_ma = values[-2], values[-1]
    prev_price, curr_price = source[-2], source[-1]
    if any(math.isnan(v) for v in (prev_ma, curr_ma, prev_price, curr_price)):
        return _insufficient_data(result)

    crossed_above = prev_price <= prev_ma and curr_price > curr_ma
    crossed_below = prev_price >= prev_ma and curr_price < curr_ma

    if crossed_above:
        reasoning = (
            f"Price ({curr_price:.2f}) crossed above {result.label} "
            f"({curr_ma:.2f}), a bullish crossover."
        )
        return RuleOutcome(
            direction=SignalDirection.BULLISH,
            reasoning=reasoning,
            threshold=curr_ma,
            strength=1.0,
        )

    if crossed_below:
        reasoning = (
            f"Price ({curr_price:.2f}) crossed below {result.label} "
            f"({curr_ma:.2f}), a bearish crossover."
        )
        return RuleOutcome(
            direction=SignalDirection.BEARISH,
            reasoning=reasoning,
            threshold=curr_ma,
            strength=1.0,
        )

    reasoning = (
        f"Price ({curr_price:.2f}) shows no crossover against "
        f"{result.label} ({curr_ma:.2f}) on the latest bar."
    )
    return RuleOutcome(
        direction=SignalDirection.NEUTRAL,
        reasoning=reasoning,
        threshold=curr_ma,
        strength=None,
    )


_RULES: Registry[RuleFn] = Registry(kind="signal rule")
_RULES.register("rsi", evaluate_threshold_rule)
_RULES.register("sma", evaluate_crossover_rule)
_RULES.register("ema", evaluate_crossover_rule)
_RULES.register("wma", evaluate_crossover_rule)


def register_rule(name: str, rule: RuleFn) -> RuleFn:
    """Register a rule for an indicator name.

    Args:
        name: Canonical indicator identifier the rule applies to.
        rule: Callable evaluating an :class:`IndicatorResult` for that
            indicator.

    Returns:
        The registered rule (for use as a decorator).

    Raises:
        ValueError: If ``name`` is already registered to a different
            rule.
    """
    return _RULES.register(name, rule)


def evaluate(result: IndicatorResult) -> RuleOutcome:
    """Evaluate the registered rule for ``result.name``.

    Args:
        result: The indicator computation to interpret.

    Returns:
        The rule's directional conclusion and reasoning.

    Raises:
        KeyError: If no rule is registered for ``result.name``.
    """
    rule = _RULES.get(result.name)
    return rule(result)
