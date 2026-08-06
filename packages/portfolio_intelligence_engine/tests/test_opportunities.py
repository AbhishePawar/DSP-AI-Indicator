"""Tests for portfolio_intelligence_engine.opportunities."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    HoldingSignal,
    IntelligenceStatus,
    rank_opportunities,
)


class TestOpportunityRanking:
    def test_empty_holdings_unavailable(self) -> None:
        result = rank_opportunities(())
        assert result.status is IntelligenceStatus.UNAVAILABLE

    def test_expected_cagr_always_empty_and_documented(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0, margin_of_safety=0.2),)
        result = rank_opportunities(holdings)
        assert result.highest_expected_cagr == ()
        assert any("forward-looking" in msg for msg in result.limitations)

    def test_ranks_by_margin_of_safety_desc(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.5, margin_of_safety=0.1),
            HoldingSignal(symbol="B", weight=0.5, margin_of_safety=0.3),
        )
        result = rank_opportunities(holdings)
        assert result.highest_margin_of_safety[0].symbol == "B"

    def test_ranks_lowest_risk_ascending(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.5, volatility=0.30),
            HoldingSignal(symbol="B", weight=0.5, volatility=0.10),
        )
        result = rank_opportunities(holdings)
        assert result.lowest_risk[0].symbol == "B"

    def test_ranks_best_quality_desc(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.5, quality_score=60.0),
            HoldingSignal(symbol="B", weight=0.5, quality_score=90.0),
        )
        result = rank_opportunities(holdings)
        assert result.best_quality[0].symbol == "B"

    def test_ranks_highest_conviction_desc(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.5, committee_confidence=0.4),
            HoldingSignal(symbol="B", weight=0.5, committee_confidence=0.9),
        )
        result = rank_opportunities(holdings)
        assert result.highest_conviction[0].symbol == "B"

    def test_partial_status_when_some_dimensions_missing(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0, margin_of_safety=0.2),)
        result = rank_opportunities(holdings)
        assert result.status is IntelligenceStatus.PARTIAL
