"""Tests for portfolio_intelligence_engine.concentration."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    AllocationKind,
    HoldingSignal,
    IntelligenceStatus,
    compute_concentration_analysis,
)


class TestConcentrationAnalysis:
    def test_empty_holdings_unavailable(self) -> None:
        result = compute_concentration_analysis(())
        assert result.status is IntelligenceStatus.UNAVAILABLE

    def test_flags_single_position_concentration(self) -> None:
        holdings = (
            HoldingSignal(symbol="AAPL", weight=0.5, sector="Information Technology"),
            HoldingSignal(symbol="MSFT", weight=0.3, sector="Information Technology"),
            HoldingSignal(symbol="JNJ", weight=0.2, sector="Health Care"),
        )
        result = compute_concentration_analysis(holdings)
        position_flags = [f for f in result.flags if f.kind is AllocationKind.POSITION]
        assert any(f.label == "AAPL" for f in position_flags)

    def test_flags_sector_concentration(self) -> None:
        holdings = (
            HoldingSignal(symbol="AAPL", weight=0.4, sector="Information Technology"),
            HoldingSignal(symbol="MSFT", weight=0.4, sector="Information Technology"),
            HoldingSignal(symbol="JNJ", weight=0.2, sector="Health Care"),
        )
        result = compute_concentration_analysis(holdings)
        sector_flags = [f for f in result.flags if f.kind is AllocationKind.SECTOR]
        assert any(f.label == "Information Technology" for f in sector_flags)

    def test_largest_holdings_sorted_desc(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.1),
            HoldingSignal(symbol="B", weight=0.6),
            HoldingSignal(symbol="C", weight=0.3),
        )
        result = compute_concentration_analysis(holdings)
        assert [h["symbol"] for h in result.largest_holdings] == ["B", "C", "A"]

    def test_herfindahl_index_single_position_is_one(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0),)
        result = compute_concentration_analysis(holdings)
        assert result.herfindahl_index == 1.0

    def test_industry_unavailable_when_not_supplied(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0),)
        result = compute_concentration_analysis(holdings)
        assert result.industry_concentration == ()
        assert any("industry" in msg for msg in result.limitations)
