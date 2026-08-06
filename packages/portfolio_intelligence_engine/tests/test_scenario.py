"""Tests for portfolio_intelligence_engine.scenario."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    HoldingSignal,
    IntelligenceStatus,
    build_scenario_summary,
)


class TestScenarioSummary:
    def test_empty_holdings_unavailable(self) -> None:
        result = build_scenario_summary((), performance=None)
        assert result.status is IntelligenceStatus.UNAVAILABLE

    def test_base_case_from_weighted_mos(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="A", weight=0.5, margin_of_safety=0.2, research_linked=True
            ),
            HoldingSignal(
                symbol="B", weight=0.5, margin_of_safety=0.0, research_linked=True
            ),
        )
        result = build_scenario_summary(
            holdings, performance={"annualized_volatility": 0.1}
        )
        base = next(c for c in result.cases if c.case == "base")
        assert base.implied_return_pct == 0.1

    def test_bull_bear_band_from_volatility(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="A", weight=1.0, margin_of_safety=0.1, research_linked=True
            ),
        )
        result = build_scenario_summary(
            holdings, performance={"annualized_volatility": 0.2}
        )
        bull = next(c for c in result.cases if c.case == "bull")
        bear = next(c for c in result.cases if c.case == "bear")
        assert bull.implied_return_pct == 0.1 + 0.2
        assert bear.implied_return_pct == 0.1 - 0.2

    def test_expected_cagr_labelled_historical(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0, margin_of_safety=0.1),)
        result = build_scenario_summary(
            holdings, performance={"annualized_return": 0.12}
        )
        assert result.expected_cagr == 0.12
        assert result.expected_cagr_basis is not None
        assert "historical" in result.expected_cagr_basis.lower()

    def test_worst_case_drawdown_from_performance(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0, margin_of_safety=0.1),)
        result = build_scenario_summary(holdings, performance={"max_drawdown": -0.4})
        assert result.worst_case_drawdown == -0.4

    def test_confidence_discounted_by_research_coverage(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="A", weight=0.5, valuation_confidence=0.8, research_linked=True
            ),
            HoldingSignal(symbol="B", weight=0.5, research_linked=False),
        )
        result = build_scenario_summary(holdings, performance=None)
        assert result.confidence == 0.8 * 0.5

    def test_cases_empty_when_no_mos_available(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0),)
        result = build_scenario_summary(holdings, performance=None)
        assert result.cases == ()
