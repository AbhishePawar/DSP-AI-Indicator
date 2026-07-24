"""Deterministic rules for interpreting a :class:`FundamentalMetric`.

A "rule" is a pure function ``FundamentalMetric -> BusinessRuleOutcome``:
it looks at what one metric computed and decides a directional bias, a
human-readable reason, and (where meaningful) the threshold that
justified it. This is the single point where metric-specific meaning
("ROE above 15% is strong profitability", "Debt-to-Equity above 1.5x is
high debt") enters the platform — everything downstream
(:mod:`fundamental.signals.signal_generator`,
:mod:`fundamental.signals.explanation_generator`,
:mod:`fundamental.signals.evidence_generator`) consumes the same
:class:`BusinessRuleOutcome` so a signal, its explanation, and its
evidence can never disagree with each other about *why* they exist.

This module intentionally mirrors the *shape* of ``dsp.signals.rules``
(a ``RuleOutcome``-like dataclass, a small family of generic rule
functions, and a name-keyed registry) without importing anything from
``dsp`` — per the architecture document's Section 4.2 dependency table,
``fundamental-engine`` depends only on ``contracts``, ``core``, and
``data-engine``. Each engine owns its own business rules and vocabulary;
converging on the same *pattern* independently is exactly what
consistent architecture across engines should look like.

Every business metric in this sprint reduces to one of two generic rule
shapes:

* "Higher is better" — profitability, growth, and cash-generation
  metrics, where a high reading is bullish and a low reading is
  bearish (:func:`evaluate_higher_is_better`).
* "Lower is better" — leverage metrics, where a high reading is
  bearish and a low reading is bullish (:func:`evaluate_lower_is_better`).

Rules are registered by metric name in a module-level
:class:`core.registry.Registry`, following the exact extension pattern
:mod:`fundamental.registry` already established for analyzers — adding a
rule for a future metric means registering a new callable, never
editing :class:`~fundamental.signals.signal_generator.BusinessSignalGenerator`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from contracts.enums import SignalDirection
from core.registry import Registry
from fundamental.models import FundamentalMetric, format_metric_value

RuleFn = Callable[[FundamentalMetric], "BusinessRuleOutcome"]


@dataclass(frozen=True, slots=True)
class BusinessRuleOutcome:
    """The result of evaluating one deterministic business rule.

    Attributes:
        direction: Directional business reading the rule concluded.
            ``BULLISH``/``BEARISH`` here describe a business
            observation ("strong profitability", "high debt"), not an
            investment recommendation.
        observation: Short, first-class label for the conclusion (e.g.
            ``"Strong Profitability"``, ``"High Debt"``), reusable by
            callers without parsing ``reasoning``.
        reasoning: Human-readable sentence explaining the conclusion.
            Reused verbatim as the basis for the accompanying
            ``contracts.Explanation`` and ``contracts.Evidence``.
        threshold: The threshold value the rule compared against, if
            any.
        strength: Normalized confidence/magnitude in ``[0.0, 1.0]``, or
            ``None`` when the rule has no meaningful strength to report
            (e.g. a neutral reading).
    """

    direction: SignalDirection
    observation: str
    reasoning: str
    threshold: float | None = None
    strength: float | None = None


def _insufficient_data(metric: FundamentalMetric) -> BusinessRuleOutcome:
    """Return the shared "not enough data" outcome for any rule."""
    return BusinessRuleOutcome(
        direction=SignalDirection.NEUTRAL,
        observation="Insufficient Data",
        reasoning=f"{metric.label} has insufficient data to produce a reading.",
        threshold=None,
        strength=None,
    )


def _strength(distance: float, span: float) -> float:
    """Normalize how far past a threshold a value sits, capped at 1.0."""
    denominator = max(abs(span), 1e-9)
    return min(1.0, distance / denominator)


def evaluate_higher_is_better(
    metric: FundamentalMetric,
    *,
    strong: float,
    weak: float,
    strong_label: str,
    weak_label: str,
) -> BusinessRuleOutcome:
    """Evaluate a metric where a higher value is a stronger business signal.

    A reading above ``strong`` is bullish; a reading below ``weak`` is
    bearish; anything in between is neutral. Applies to profitability,
    growth, and cash-generation metrics (e.g. ROE, revenue growth, free
    cash flow).

    Args:
        metric: The computed metric to interpret.
        strong: Threshold above which the reading is bullish.
        weak: Threshold below which the reading is bearish. Must be
            less than or equal to ``strong``.
        strong_label: Business observation label for a bullish reading
            (e.g. ``"Strong Profitability"``).
        weak_label: Business observation label for a bearish reading
            (e.g. ``"Weak Profitability"``).

    Returns:
        The rule's directional conclusion and reasoning.
    """
    value = metric.value
    if value is None:
        return _insufficient_data(metric)
    unit = metric.unit

    if value > strong:
        reasoning = (
            f"{metric.label} is {format_metric_value(value, unit)}, above the "
            f"threshold of {format_metric_value(strong, unit)} associated with "
            f"{strong_label.lower()}."
        )
        return BusinessRuleOutcome(
            direction=SignalDirection.BULLISH,
            observation=strong_label,
            reasoning=reasoning,
            threshold=strong,
            strength=_strength(value - strong, strong),
        )

    if value < weak:
        reasoning = (
            f"{metric.label} is {format_metric_value(value, unit)}, below the "
            f"threshold of {format_metric_value(weak, unit)} associated with "
            f"{weak_label.lower()}."
        )
        return BusinessRuleOutcome(
            direction=SignalDirection.BEARISH,
            observation=weak_label,
            reasoning=reasoning,
            threshold=weak,
            strength=_strength(weak - value, weak),
        )

    reasoning = (
        f"{metric.label} is {format_metric_value(value, unit)}, within the "
        f"neutral range [{format_metric_value(weak, unit)}, "
        f"{format_metric_value(strong, unit)}]."
    )
    return BusinessRuleOutcome(
        direction=SignalDirection.NEUTRAL,
        observation=f"Moderate {metric.label}",
        reasoning=reasoning,
        threshold=None,
        strength=None,
    )


def evaluate_lower_is_better(
    metric: FundamentalMetric,
    *,
    healthy: float,
    high: float,
    healthy_label: str,
    high_label: str,
) -> BusinessRuleOutcome:
    """Evaluate a metric where a lower value is a stronger business signal.

    A reading above ``high`` is bearish; a reading below ``healthy`` is
    bullish; anything in between is neutral. Applies to leverage
    metrics (e.g. Debt-to-Equity), where the mirror image of
    :func:`evaluate_higher_is_better` holds.

    Args:
        metric: The computed metric to interpret.
        healthy: Threshold below which the reading is bullish.
        high: Threshold above which the reading is bearish. Must be
            greater than or equal to ``healthy``.
        healthy_label: Business observation label for a bullish reading
            (e.g. ``"Healthy Balance Sheet"``).
        high_label: Business observation label for a bearish reading
            (e.g. ``"High Debt"``).

    Returns:
        The rule's directional conclusion and reasoning.
    """
    value = metric.value
    if value is None:
        return _insufficient_data(metric)
    unit = metric.unit

    if value > high:
        reasoning = (
            f"{metric.label} is {format_metric_value(value, unit)}, above the "
            f"threshold of {format_metric_value(high, unit)} associated with "
            f"{high_label.lower()}."
        )
        return BusinessRuleOutcome(
            direction=SignalDirection.BEARISH,
            observation=high_label,
            reasoning=reasoning,
            threshold=high,
            strength=_strength(value - high, high),
        )

    if value < healthy:
        reasoning = (
            f"{metric.label} is {format_metric_value(value, unit)}, below the "
            f"threshold of {format_metric_value(healthy, unit)} associated with "
            f"{healthy_label.lower()}."
        )
        return BusinessRuleOutcome(
            direction=SignalDirection.BULLISH,
            observation=healthy_label,
            reasoning=reasoning,
            threshold=healthy,
            strength=_strength(healthy - value, healthy),
        )

    reasoning = (
        f"{metric.label} is {format_metric_value(value, unit)}, within the "
        f"neutral range [{format_metric_value(healthy, unit)}, "
        f"{format_metric_value(high, unit)}]."
    )
    return BusinessRuleOutcome(
        direction=SignalDirection.NEUTRAL,
        observation=f"Moderate {metric.label}",
        reasoning=reasoning,
        threshold=None,
        strength=None,
    )


_RULES: Registry[RuleFn] = Registry(kind="business rule")
_RULES.register(
    "roe",
    partial(
        evaluate_higher_is_better,
        strong=0.15,
        weak=0.05,
        strong_label="Strong Profitability",
        weak_label="Weak Profitability",
    ),
)
_RULES.register(
    "roce",
    partial(
        evaluate_higher_is_better,
        strong=0.15,
        weak=0.05,
        strong_label="Efficient Capital Use",
        weak_label="Inefficient Capital Use",
    ),
)
_RULES.register(
    "operating_margin",
    partial(
        evaluate_higher_is_better,
        strong=0.15,
        weak=0.05,
        strong_label="Strong Operating Efficiency",
        weak_label="Weak Operating Efficiency",
    ),
)
_RULES.register(
    "revenue_growth",
    partial(
        evaluate_higher_is_better,
        strong=0.10,
        weak=0.0,
        strong_label="Strong Revenue Growth",
        weak_label="Weak Revenue Growth",
    ),
)
_RULES.register(
    "eps_growth",
    partial(
        evaluate_higher_is_better,
        strong=0.10,
        weak=0.0,
        strong_label="Strong Earnings Growth",
        weak_label="Weak Earnings Growth",
    ),
)
_RULES.register(
    "free_cash_flow",
    partial(
        evaluate_higher_is_better,
        strong=0.0,
        weak=0.0,
        strong_label="Healthy Cash Generation",
        weak_label="Negative Cash Flow",
    ),
)
_RULES.register(
    "debt_to_equity",
    partial(
        evaluate_lower_is_better,
        healthy=0.5,
        high=1.5,
        healthy_label="Healthy Balance Sheet",
        high_label="High Debt",
    ),
)


def register_rule(name: str, rule: RuleFn) -> RuleFn:
    """Register a rule for a metric name.

    Args:
        name: Canonical metric identifier the rule applies to.
        rule: Callable evaluating a :class:`FundamentalMetric` for that
            metric.

    Returns:
        The registered rule (for use as a decorator).

    Raises:
        ValueError: If ``name`` is already registered to a different
            rule.
    """
    return _RULES.register(name, rule)


def evaluate(metric: FundamentalMetric) -> BusinessRuleOutcome:
    """Evaluate the registered rule for ``metric.name``.

    Args:
        metric: The computed metric to interpret.

    Returns:
        The rule's directional conclusion and reasoning.

    Raises:
        KeyError: If no rule is registered for ``metric.name``.
    """
    rule = _RULES.get(metric.name)
    return rule(metric)
