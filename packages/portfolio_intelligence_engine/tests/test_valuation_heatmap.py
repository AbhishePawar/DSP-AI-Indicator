"""Tests for portfolio_intelligence_engine.valuation_heatmap."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    HoldingSignal,
    IntelligenceStatus,
    ValuationClass,
    classify_valuation,
    compute_valuation_heatmap,
)


class TestClassifyValuation:
    def test_undervalued_above_threshold(self) -> None:
        assert classify_valuation(0.20) is ValuationClass.UNDERVALUED

    def test_overvalued_below_threshold(self) -> None:
        assert classify_valuation(-0.30) is ValuationClass.OVERVALUED

    def test_fairly_valued_in_band(self) -> None:
        assert classify_valuation(0.02) is ValuationClass.FAIRLY_VALUED

    def test_unavailable_when_none(self) -> None:
        assert classify_valuation(None) is ValuationClass.UNAVAILABLE

    def test_boundary_is_undervalued(self) -> None:
        assert classify_valuation(0.15) is ValuationClass.UNDERVALUED

    def test_boundary_is_overvalued(self) -> None:
        assert classify_valuation(-0.15) is ValuationClass.OVERVALUED


class TestComputeValuationHeatmap:
    def test_empty_holdings_unavailable(self) -> None:
        result = compute_valuation_heatmap(())
        assert result.status is IntelligenceStatus.UNAVAILABLE

    def test_mixed_holdings_complete_when_all_linked(self) -> None:
        holdings = (
            HoldingSignal(symbol="AAPL", weight=0.5, margin_of_safety=0.25),
            HoldingSignal(symbol="TSLA", weight=0.5, margin_of_safety=-0.30),
        )
        result = compute_valuation_heatmap(holdings)
        assert result.status is IntelligenceStatus.COMPLETE
        assert result.undervalued_weight == 0.5
        assert result.overvalued_weight == 0.5
        assert result.unavailable_weight == 0.0

    def test_partial_when_some_missing(self) -> None:
        holdings = (
            HoldingSignal(symbol="AAPL", weight=0.5, margin_of_safety=0.25),
            HoldingSignal(symbol="XYZ", weight=0.5),
        )
        result = compute_valuation_heatmap(holdings)
        assert result.status is IntelligenceStatus.PARTIAL
        assert result.unavailable_weight == 0.5
        xyz_row = next(r for r in result.rows if r.symbol == "XYZ")
        assert xyz_row.message is not None
        assert "Data unavailable" in xyz_row.message

    def test_all_missing_is_unavailable_status(self) -> None:
        holdings = (HoldingSignal(symbol="XYZ", weight=1.0),)
        result = compute_valuation_heatmap(holdings)
        assert result.status is IntelligenceStatus.UNAVAILABLE
