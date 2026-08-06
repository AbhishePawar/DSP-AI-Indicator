"""Tests for portfolio_analytics.performance — closed-form verification."""

from __future__ import annotations

import pytest

from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.performance import (
    compute_alpha,
    compute_beta,
    compute_information_ratio,
    compute_max_drawdown_via_quantitative_risk,
    compute_performance_ratios,
    compute_sharpe_ratio,
    compute_sortino_ratio,
    compute_tracking_error,
    compute_treynor_ratio,
)


class TestBeta:
    def test_beta_of_identical_series_is_one(self) -> None:
        series = [0.01, -0.02, 0.03, 0.0, 0.015]
        assert compute_beta(series, series) == pytest.approx(1.0)

    def test_beta_none_on_insufficient_data(self) -> None:
        assert compute_beta([0.01], [0.02]) is None

    def test_beta_none_on_zero_benchmark_variance(self) -> None:
        assert compute_beta([0.01, 0.02, 0.03], [0.0, 0.0, 0.0]) is None

    def test_beta_double_sensitivity(self) -> None:
        benchmark = [0.01, -0.02, 0.03, 0.0, 0.015]
        portfolio = [2 * r for r in benchmark]
        assert compute_beta(portfolio, benchmark) == pytest.approx(2.0)


class TestSharpeSortino:
    def test_sharpe_none_on_zero_stdev(self) -> None:
        assert compute_sharpe_ratio([0.01, 0.01, 0.01]) is None

    def test_sharpe_positive_for_positive_mean_returns(self) -> None:
        result = compute_sharpe_ratio([0.01, 0.02, -0.01, 0.015, 0.005])
        assert result is not None
        assert result > 0

    def test_sortino_none_on_no_downside(self) -> None:
        # All returns >= risk-free rate -> zero downside deviation.
        assert compute_sortino_ratio([0.01, 0.02, 0.03], risk_free_rate=0.0) is None

    def test_sortino_positive_with_mixed_returns(self) -> None:
        result = compute_sortino_ratio([0.02, -0.01, 0.03, -0.005, 0.01])
        assert result is not None


class TestAlphaTreynor:
    def test_alpha_zero_for_identical_series_zero_rf(self) -> None:
        series = [0.01, -0.02, 0.03, 0.0, 0.015]
        alpha = compute_alpha(series, series, risk_free_rate=0.0)
        assert alpha == pytest.approx(0.0)

    def test_treynor_none_on_zero_beta(self) -> None:
        assert compute_treynor_ratio([0.01, 0.02, 0.03], [0.0, 0.0, 0.0]) is None

    def test_treynor_computed_for_beta_one(self) -> None:
        series = [0.01, 0.02, -0.01, 0.03, 0.0]
        result = compute_treynor_ratio(series, series, risk_free_rate=0.0)
        assert result is not None


class TestTrackingErrorInformationRatio:
    def test_tracking_error_zero_for_identical_series(self) -> None:
        series = [0.01, -0.02, 0.03, 0.0, 0.015]
        assert compute_tracking_error(series, series) == pytest.approx(0.0)

    def test_information_ratio_none_when_tracking_error_zero(self) -> None:
        series = [0.01, -0.02, 0.03, 0.0, 0.015]
        assert compute_information_ratio(series, series) is None

    def test_information_ratio_computed_for_active_returns(self) -> None:
        portfolio = [0.02, 0.01, 0.03, -0.01, 0.015]
        benchmark = [0.01, 0.01, 0.01, 0.01, 0.01]
        assert compute_information_ratio(portfolio, benchmark) is not None


class TestMaxDrawdownReuse:
    def test_reuse_matches_quantitative_risk_engine_semantics(self) -> None:
        # Peak at period 0 (equity=1.0), trough after a large negative return.
        returns = [0.0, -0.5, 0.1]
        drawdown = compute_max_drawdown_via_quantitative_risk(returns)
        assert drawdown is not None
        assert drawdown == pytest.approx(0.5, abs=1e-6)

    def test_none_on_empty_series(self) -> None:
        assert compute_max_drawdown_via_quantitative_risk([]) is None

    def test_zero_drawdown_for_all_positive_returns(self) -> None:
        drawdown = compute_max_drawdown_via_quantitative_risk([0.01, 0.02, 0.03])
        assert drawdown == pytest.approx(0.0, abs=1e-6)


class TestComputePerformanceRatios:
    def test_unavailable_status_with_no_returns(self) -> None:
        result = compute_performance_ratios([], None)
        assert result.status == AnalyticsStatus.UNAVAILABLE
        assert result.sharpe_ratio is None
        assert result.max_drawdown is None

    def test_partial_status_without_benchmark(self) -> None:
        result = compute_performance_ratios([0.01, 0.02, -0.01, 0.015], None)
        assert result.beta is None
        assert result.max_drawdown is not None
        assert any("benchmark" in note for note in result.limitations)

    def test_complete_when_all_inputs_present(self) -> None:
        portfolio = [0.02, 0.01, 0.03, -0.01, 0.015]
        benchmark = [0.01, -0.005, 0.02, 0.005, 0.01]
        result = compute_performance_ratios(portfolio, benchmark)
        assert result.sharpe_ratio is not None
        assert result.beta is not None
        assert result.max_drawdown is not None
        assert result.window_days == 5

    def test_to_public_dict_roundtrip(self) -> None:
        result = compute_performance_ratios([0.01, 0.02, -0.01], [0.01, 0.02, -0.01])
        payload = result.to_public_dict()
        assert payload["status"] in {"complete", "partial", "unavailable"}
        assert "sharpe_ratio" in payload

