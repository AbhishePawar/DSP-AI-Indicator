"""Tests for portfolio_intelligence_engine.health_score."""

from __future__ import annotations

import pytest

from portfolio_intelligence_engine import (
    HoldingSignal,
    IntelligenceStatus,
    compute_concentration_analysis,
    compute_diversification_score,
    compute_health_score,
)


def _diversification_and_concentration(holdings):
    return (
        compute_diversification_score(holdings, correlation_matrix=None),
        compute_concentration_analysis(holdings),
    )


class TestHealthScore:
    def test_empty_holdings_unavailable(self) -> None:
        div, conc = _diversification_and_concentration(())
        result = compute_health_score(
            (), performance=None, diversification=div, concentration=conc
        )
        assert result.status is IntelligenceStatus.UNAVAILABLE

    def test_partial_when_only_diversification_and_concentration_available(
        self,
    ) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0),)
        div, conc = _diversification_and_concentration(holdings)
        result = compute_health_score(
            holdings, performance=None, diversification=div, concentration=conc
        )
        assert result.status is IntelligenceStatus.PARTIAL
        assert result.score is not None
        component_names = {c.name for c in result.components if c.available}
        assert component_names == {"diversification", "concentration"}

    def test_complete_when_all_inputs_present(self) -> None:
        holdings = (
            HoldingSignal(
                symbol="A",
                weight=0.6,
                margin_of_safety=0.2,
                quality_score=80.0,
                sector="Financials",
            ),
            HoldingSignal(
                symbol="B",
                weight=0.4,
                margin_of_safety=0.1,
                quality_score=70.0,
                sector="Health Care",
            ),
        )
        div, conc = _diversification_and_concentration(holdings)
        performance = {"annualized_volatility": 0.15, "max_drawdown": -0.2}
        result = compute_health_score(
            holdings,
            performance=performance,
            diversification=div,
            concentration=conc,
            cash_weight=0.05,
        )
        assert result.status is IntelligenceStatus.COMPLETE
        assert result.score is not None
        assert 0.0 <= result.score <= 100.0

    def test_higher_mos_and_quality_scores_higher(self) -> None:
        base_holdings = (
            HoldingSignal(
                symbol="A", weight=1.0, margin_of_safety=0.0, quality_score=50.0
            ),
        )
        good_holdings = (
            HoldingSignal(
                symbol="A", weight=1.0, margin_of_safety=0.3, quality_score=90.0
            ),
        )
        div1, conc1 = _diversification_and_concentration(base_holdings)
        div2, conc2 = _diversification_and_concentration(good_holdings)
        low = compute_health_score(
            base_holdings, performance=None, diversification=div1, concentration=conc1
        )
        high = compute_health_score(
            good_holdings, performance=None, diversification=div2, concentration=conc2
        )
        assert high.score > low.score

    def test_weights_are_renormalized_among_available(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0),)
        div, conc = _diversification_and_concentration(holdings)
        result = compute_health_score(
            holdings, performance=None, diversification=div, concentration=conc
        )
        available = [c for c in result.components if c.available]
        assert sum(c.contribution for c in available) == pytest.approx(result.score)
