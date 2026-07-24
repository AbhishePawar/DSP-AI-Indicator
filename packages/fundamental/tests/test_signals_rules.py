"""Tests for fundamental.signals.rules."""

from datetime import date

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, SignalDirection
from fundamental.enums import MetricUnit
from fundamental.models import FundamentalMetric
from fundamental.signals.rules import (
    evaluate,
    evaluate_higher_is_better,
    evaluate_lower_is_better,
    register_rule,
)

_INSTRUMENT = Instrument(symbol="TEST", asset_class=AssetClass.EQUITY, currency="USD")


def _metric(name: str, value: float | None, unit: MetricUnit) -> FundamentalMetric:
    return FundamentalMetric(
        instrument=_INSTRUMENT,
        name=name,
        value=value,
        unit=unit,
        period_end=date(2024, 12, 31),
    )


class TestEvaluateHigherIsBetter:
    """Tests for the "higher value is bullish" rule family."""

    def _run(self, value: float | None):
        metric = _metric("roe", value, MetricUnit.PERCENT)
        return evaluate_higher_is_better(
            metric,
            strong=0.15,
            weak=0.05,
            strong_label="Strong Profitability",
            weak_label="Weak Profitability",
        )

    def test_above_strong_is_bullish(self) -> None:
        outcome = self._run(0.20)
        assert outcome.direction is SignalDirection.BULLISH
        assert outcome.observation == "Strong Profitability"
        assert "18.0%" not in outcome.reasoning  # sanity: not fabricating text
        assert "20.0%" in outcome.reasoning

    def test_below_weak_is_bearish(self) -> None:
        outcome = self._run(0.02)
        assert outcome.direction is SignalDirection.BEARISH
        assert outcome.observation == "Weak Profitability"

    def test_between_thresholds_is_neutral(self) -> None:
        outcome = self._run(0.10)
        assert outcome.direction is SignalDirection.NEUTRAL
        assert outcome.threshold is None

    def test_none_value_is_insufficient_data(self) -> None:
        outcome = self._run(None)
        assert outcome.direction is SignalDirection.NEUTRAL
        assert outcome.observation == "Insufficient Data"

    def test_strength_is_capped_at_one(self) -> None:
        outcome = self._run(100.0)
        assert outcome.strength == 1.0


class TestEvaluateLowerIsBetter:
    """Tests for the "lower value is bullish" rule family."""

    def _run(self, value: float | None):
        metric = _metric("debt_to_equity", value, MetricUnit.RATIO)
        return evaluate_lower_is_better(
            metric,
            healthy=0.5,
            high=1.5,
            healthy_label="Healthy Balance Sheet",
            high_label="High Debt",
        )

    def test_above_high_is_bearish(self) -> None:
        outcome = self._run(2.0)
        assert outcome.direction is SignalDirection.BEARISH
        assert outcome.observation == "High Debt"

    def test_below_healthy_is_bullish(self) -> None:
        outcome = self._run(0.2)
        assert outcome.direction is SignalDirection.BULLISH
        assert outcome.observation == "Healthy Balance Sheet"

    def test_between_thresholds_is_neutral(self) -> None:
        outcome = self._run(1.0)
        assert outcome.direction is SignalDirection.NEUTRAL


class TestRuleRegistry:
    """Tests for the metric-name -> rule dispatch registry."""

    def test_default_rules_cover_every_sprint_metric(self) -> None:
        for name in (
            "roe",
            "roce",
            "operating_margin",
            "revenue_growth",
            "eps_growth",
            "free_cash_flow",
            "debt_to_equity",
        ):
            metric = _metric(name, 0.10, MetricUnit.PERCENT)
            outcome = evaluate(metric)
            assert outcome.direction is not None

    def test_unregistered_metric_raises_key_error(self) -> None:
        metric = _metric("current_ratio", 1.5, MetricUnit.RATIO)
        with pytest.raises(KeyError):
            evaluate(metric)

    def test_register_rule_adds_new_dispatch(self) -> None:
        def rule(metric: FundamentalMetric):
            return evaluate_higher_is_better(
                metric,
                strong=1.0,
                weak=0.5,
                strong_label="Strong Current Ratio",
                weak_label="Weak Current Ratio",
            )

        register_rule("current_ratio_test", rule)
        metric = _metric("current_ratio_test", 1.5, MetricUnit.RATIO)
        outcome = evaluate(metric)
        assert outcome.observation == "Strong Current Ratio"

    def test_conflicting_rule_registration_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="already registered"):
            register_rule("roe", lambda metric: evaluate(metric))
