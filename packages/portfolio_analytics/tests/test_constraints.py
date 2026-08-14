"""Tests for portfolio_analytics.constraints — Position Limits + Rebalancing."""

from __future__ import annotations

import pytest

from portfolio_analytics.constraints import (
    check_position_limits,
    compute_rebalancing_plan,
)
from portfolio_analytics.enums import AnalyticsStatus, RebalancingAction
from portfolio_analytics.models import PositionInput


class TestPositionLimits:
    def test_no_checks_when_no_limits_supplied(self) -> None:
        report = check_position_limits([PositionInput(symbol="AAA", weight=0.5)])
        assert report.status == AnalyticsStatus.UNAVAILABLE
        assert report.checks == ()

    def test_flags_position_limit_breach(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.25),
            PositionInput(symbol="BBB", weight=0.10),
        ]
        report = check_position_limits(positions, max_position_weight=0.20)
        breached_symbols = {b.label for b in report.breaches}
        assert breached_symbols == {"AAA"}

    def test_flags_sector_limit_breach(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.20, sector="Technology"),
            PositionInput(symbol="BBB", weight=0.20, sector="Technology"),
        ]
        report = check_position_limits(positions, max_sector_weight=0.30)
        breach = next(b for b in report.breaches if b.limit_type == "max_sector_weight")
        assert breach.label == "Technology"
        assert breach.actual_value == pytest.approx(0.40)

    def test_cash_limit_breach(self) -> None:
        report = check_position_limits(
            [], min_cash_weight=0.05, cash_weight=0.02
        )
        assert report.breaches[0].label == "cash"
        assert report.breaches[0].breached is True

    def test_sector_specific_override(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=0.5, sector="Energy")]
        report = check_position_limits(
            positions,
            max_sector_weight=0.30,
            sector_limits={"Energy": 0.60},
        )
        breach = next(b for b in report.checks if b.limit_type == "max_sector_weight")
        assert breach.breached is False


class TestRebalancingPlan:
    def test_unavailable_without_targets(self) -> None:
        plan = compute_rebalancing_plan([PositionInput(symbol="AAA", weight=0.5)], {})
        assert plan.status == AnalyticsStatus.UNAVAILABLE

    def test_suggests_decrease_when_overweight(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=0.30)]
        plan = compute_rebalancing_plan(positions, {"AAA": 0.20})
        trade = plan.trades[0]
        assert trade.suggested_action == RebalancingAction.DECREASE
        assert trade.suggested_delta_weight == pytest.approx(-0.10)

    def test_suggests_increase_when_underweight(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=0.10)]
        plan = compute_rebalancing_plan(positions, {"AAA": 0.20})
        trade = plan.trades[0]
        assert trade.suggested_action == RebalancingAction.INCREASE

    def test_hold_within_threshold(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=0.205)]
        plan = compute_rebalancing_plan(
            positions, {"AAA": 0.20}, drift_threshold=0.01
        )
        assert plan.trades[0].suggested_action == RebalancingAction.HOLD

    def test_disclaimer_present(self) -> None:
        plan = compute_rebalancing_plan(
            [PositionInput(symbol="AAA", weight=0.5)], {"AAA": 0.5}
        )
        assert "not a trade" in plan.disclaimer.lower()

    def test_includes_target_only_symbol(self) -> None:
        plan = compute_rebalancing_plan([], {"NEWSYM": 0.10})
        assert plan.trades[0].symbol == "NEWSYM"
        assert plan.trades[0].suggested_action == RebalancingAction.INCREASE
