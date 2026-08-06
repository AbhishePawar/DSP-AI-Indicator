"""Tests for portfolio_analytics.stress — Scenario Analysis + Stress Testing."""

from __future__ import annotations

from datetime import date

import pytest

from portfolio_analytics.models import PositionInput
from portfolio_analytics.ports import DailyReturn
from portfolio_analytics.stress import compute_scenario_impact, compute_stress_test


class TestScenarioImpact:
    def test_market_wide_shock_with_default_beta(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.5),
            PositionInput(symbol="BBB", weight=0.5),
        ]
        impact = compute_scenario_impact(
            "market -20%", -0.20, positions=positions
        )
        assert impact.portfolio_impact_pct == pytest.approx(-0.20)
        assert impact.per_position_impact_pct["AAA"] == pytest.approx(-0.20)

    def test_per_position_beta_override(self) -> None:
        positions = [
            PositionInput(symbol="AAA", weight=0.5),
            PositionInput(symbol="BBB", weight=0.5),
        ]
        impact = compute_scenario_impact(
            "market -10%",
            -0.10,
            positions=positions,
            betas={"AAA": 2.0, "BBB": 0.5},
        )
        assert impact.per_position_impact_pct["AAA"] == pytest.approx(-0.20)
        assert impact.per_position_impact_pct["BBB"] == pytest.approx(-0.05)
        assert impact.portfolio_impact_pct == pytest.approx(-0.125)

    def test_excludes_positions_with_no_beta(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0)]
        impact = compute_scenario_impact(
            "shock", -0.10, positions=positions, betas={"AAA": None}
        )
        assert impact.portfolio_impact_pct is None
        assert impact.per_position_impact_pct == {}


class TestStressTest:
    def test_uses_actual_history_when_available(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0)]
        returns_by_symbol = {
            "AAA": (
                DailyReturn(trade_date=date(2020, 3, 1), return_value=-0.10),
                DailyReturn(trade_date=date(2020, 3, 2), return_value=-0.05),
            )
        }
        result = compute_stress_test(
            scenario_id="covid_crash",
            description="2020 COVID crash",
            window_start=date(2020, 3, 1),
            window_end=date(2020, 3, 2),
            positions=positions,
            returns_by_symbol=returns_by_symbol,
        )
        expected = (1 - 0.10) * (1 - 0.05) - 1
        assert result.portfolio_return_pct == pytest.approx(expected)
        assert result.positions_with_history == 1
        assert result.positions_beta_scaled == 0

    def test_falls_back_to_beta_scaled_benchmark_shock(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0)]
        result = compute_stress_test(
            scenario_id="2008_crash",
            description="2008 financial crisis",
            window_start=date(2008, 9, 1),
            window_end=date(2008, 10, 1),
            positions=positions,
            returns_by_symbol={"AAA": None},
            betas={"AAA": 1.5},
            benchmark_shock_pct=-0.30,
        )
        assert result.portfolio_return_pct == pytest.approx(-0.45)
        assert result.positions_beta_scaled == 1
        assert result.positions_with_history == 0

    def test_unavailable_position_excluded_entirely(self) -> None:
        positions = [PositionInput(symbol="AAA", weight=1.0)]
        result = compute_stress_test(
            scenario_id="x",
            description="x",
            window_start=date(2020, 1, 1),
            window_end=date(2020, 1, 2),
            positions=positions,
            returns_by_symbol={"AAA": None},
        )
        assert result.portfolio_return_pct is None
