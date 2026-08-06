"""Tests for portfolio_intelligence_engine.diversification."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    HoldingSignal,
    IntelligenceStatus,
    compute_diversification_score,
)


class TestDiversificationScore:
    def test_empty_holdings_unavailable(self) -> None:
        result = compute_diversification_score((), correlation_matrix=None)
        assert result.status is IntelligenceStatus.UNAVAILABLE

    def test_partial_without_correlation_matrix(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0),)
        result = compute_diversification_score(holdings, correlation_matrix=None)
        assert result.status is IntelligenceStatus.PARTIAL
        assert result.average_pairwise_correlation is None

    def test_more_holdings_scores_higher_than_single_position(self) -> None:
        single = compute_diversification_score(
            (HoldingSignal(symbol="A", weight=1.0),), correlation_matrix=None
        )
        many = compute_diversification_score(
            tuple(
                HoldingSignal(symbol=f"S{i}", weight=0.1, sector=f"Sector{i}")
                for i in range(10)
            ),
            correlation_matrix=None,
        )
        assert many.score is not None
        assert single.score is not None
        assert many.score > single.score

    def test_average_pairwise_correlation_computed(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.5),
            HoldingSignal(symbol="B", weight=0.5),
        )
        matrix = {
            "symbols": ["A", "B"],
            "matrix": [[1.0, 0.4], [0.4, 1.0]],
        }
        result = compute_diversification_score(holdings, correlation_matrix=matrix)
        assert result.average_pairwise_correlation == 0.4

    def test_holding_count_and_sector_count_reported(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.5, sector="Financials"),
            HoldingSignal(symbol="B", weight=0.5, sector="Health Care"),
        )
        result = compute_diversification_score(holdings, correlation_matrix=None)
        assert result.holding_count == 2
        assert result.sector_count == 2
