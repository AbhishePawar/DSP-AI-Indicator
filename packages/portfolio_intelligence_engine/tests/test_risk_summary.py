"""Tests for portfolio_intelligence_engine.risk_summary."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    HoldingSignal,
    IntelligenceStatus,
    build_risk_summary,
)


class TestRiskSummary:
    def test_unavailable_with_no_inputs(self) -> None:
        result = build_risk_summary(
            (), performance=None, monte_carlo=None, stress_tests=None
        )
        assert result.status is IntelligenceStatus.UNAVAILABLE
        assert result.beta is None

    def test_pulls_performance_fields_through(self) -> None:
        performance = {
            "beta": 1.2,
            "annualized_volatility": 0.18,
            "max_drawdown": -0.25,
            "tracking_error": 0.05,
        }
        result = build_risk_summary(
            (HoldingSignal(symbol="A", weight=1.0),),
            performance=performance,
            monte_carlo=None,
            stress_tests=None,
        )
        assert result.beta == 1.2
        assert result.annualized_volatility == 0.18
        assert result.max_drawdown == -0.25
        assert result.tracking_error == 0.05

    def test_var_derived_from_monte_carlo_p5(self) -> None:
        monte_carlo = {"percentiles": {"p5": -0.20, "p50": 0.05, "p95": 0.30}}
        result = build_risk_summary(
            (HoldingSignal(symbol="A", weight=1.0),),
            performance=None,
            monte_carlo=monte_carlo,
            stress_tests=None,
        )
        assert result.value_at_risk_95 == 0.20
        assert result.value_at_risk_method is not None

    def test_cvar_is_always_unavailable(self) -> None:
        result = build_risk_summary(
            (), performance=None, monte_carlo=None, stress_tests=None
        )
        assert result.conditional_value_at_risk_95 is None
        assert any("Conditional VaR" in msg for msg in result.limitations)

    def test_highlights_highest_risk_holdings_by_contribution(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="A", weight=0.5, volatility=0.10, risk_contribution_pct=20.0
            ),
            HoldingSignal(
                symbol="B", weight=0.5, volatility=0.40, risk_contribution_pct=80.0
            ),
        )
        result = build_risk_summary(
            holdings, performance=None, monte_carlo=None, stress_tests=None
        )
        assert result.highest_risk_holdings[0].symbol == "B"

    def test_stress_test_count_only_counts_available(self) -> None:
        stress_tests = [{"available": True}, {"available": False}]
        result = build_risk_summary(
            (HoldingSignal(symbol="A", weight=1.0),),
            performance=None,
            monte_carlo=None,
            stress_tests=stress_tests,
        )
        assert result.stress_test_count == 1
