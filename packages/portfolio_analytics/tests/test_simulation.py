"""Tests for portfolio_analytics.simulation — Monte Carlo + Efficient Frontier."""

from __future__ import annotations

from datetime import date

from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.ports import DailyReturn
from portfolio_analytics.returns import align_return_series
from portfolio_analytics.simulation import (
    compute_efficient_frontier,
    compute_monte_carlo,
)


def _series(values: list[float]) -> tuple[DailyReturn, ...]:
    return tuple(
        DailyReturn(trade_date=date(2024, 1, i + 1), return_value=v)
        for i, v in enumerate(values)
    )


class TestMonteCarlo:
    def test_unavailable_on_insufficient_history(self) -> None:
        result = compute_monte_carlo([0.01])
        assert result.status == AnalyticsStatus.UNAVAILABLE

    def test_deterministic_with_fixed_seed(self) -> None:
        history = [0.01, -0.02, 0.03, 0.0, 0.015, -0.005]
        a = compute_monte_carlo(history, paths=200, horizon_days=30, seed=42)
        b = compute_monte_carlo(history, paths=200, horizon_days=30, seed=42)
        assert a.percentiles == b.percentiles
        assert a.mean_terminal_return == b.mean_terminal_return

    def test_percentiles_are_ordered(self) -> None:
        history = [0.02, -0.03, 0.01, 0.04, -0.01, 0.015]
        result = compute_monte_carlo(history, paths=500, horizon_days=60, seed=7)
        assert result.status == AnalyticsStatus.COMPLETE
        p = result.percentiles
        assert p["p5"] <= p["p25"] <= p["p50"] <= p["p75"] <= p["p95"]

    def test_all_positive_history_yields_positive_terminal_returns(self) -> None:
        history = [0.01, 0.02, 0.015]
        result = compute_monte_carlo(history, paths=50, horizon_days=10, seed=1)
        assert result.percentiles["p5"] > 0


class TestEfficientFrontier:
    def test_unavailable_with_single_symbol(self) -> None:
        aligned = align_return_series({"AAA": _series([0.01, 0.02, -0.01])})
        assert aligned is not None
        result = compute_efficient_frontier(aligned, samples=10, seed=1)
        assert result.status == AnalyticsStatus.UNAVAILABLE

    def test_produces_non_dominated_points(self) -> None:
        aligned = align_return_series(
            {
                "AAA": _series([0.02, -0.01, 0.03, 0.0, 0.01]),
                "BBB": _series([0.01, 0.01, -0.02, 0.02, 0.015]),
            }
        )
        assert aligned is not None
        result = compute_efficient_frontier(aligned, samples=100, seed=3)
        assert result.status == AnalyticsStatus.COMPLETE
        assert len(result.points) >= 1
        # No point should be dominated by another in the returned frontier.
        for i, point in enumerate(result.points):
            for j, other in enumerate(result.points):
                if i == j:
                    continue
                dominated = (
                    other.expected_return >= point.expected_return
                    and other.volatility <= point.volatility
                    and (
                        other.expected_return > point.expected_return
                        or other.volatility < point.volatility
                    )
                )
                assert not dominated

    def test_current_portfolio_point_included_when_weights_supplied(self) -> None:
        aligned = align_return_series(
            {
                "AAA": _series([0.02, -0.01, 0.03, 0.0, 0.01]),
                "BBB": _series([0.01, 0.01, -0.02, 0.02, 0.015]),
            }
        )
        assert aligned is not None
        result = compute_efficient_frontier(
            aligned, current_weights={"AAA": 0.5, "BBB": 0.5}, samples=20, seed=5
        )
        assert result.current_portfolio_point is not None
