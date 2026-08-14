"""Tests for portfolio_intelligence_engine.drift."""

from __future__ import annotations

from portfolio_intelligence_engine import (
    DriftDirection,
    HoldingSignal,
    IntelligenceStatus,
    compute_drift_analysis,
)
from portfolio_intelligence_engine.reference import GICS_SECTORS


class TestDriftAnalysis:
    def test_empty_holdings_unavailable(self) -> None:
        result = compute_drift_analysis(())
        assert result.status is IntelligenceStatus.UNAVAILABLE

    def test_missing_sectors_detected(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=1.0, sector="Information Technology"),
        )
        result = compute_drift_analysis(holdings)
        assert "Energy" in result.missing_sectors
        assert len(result.missing_sectors) == len(GICS_SECTORS) - 1

    def test_overweight_sector_flagged(self) -> None:
        holdings = tuple(
            HoldingSignal(
                symbol=f"S{i}", weight=1.0 / 5, sector="Information Technology"
            )
            for i in range(5)
        )
        result = compute_drift_analysis(holdings)
        tech_row = next(
            r for r in result.sector_drift if r.label == "Information Technology"
        )
        assert tech_row.direction is DriftDirection.OVERWEIGHT

    def test_style_unavailable_without_caller_labels(self) -> None:
        holdings = (HoldingSignal(symbol="A", weight=1.0, sector="Financials"),)
        result = compute_drift_analysis(holdings)
        assert result.style_drift == ()
        assert any("style" in msg for msg in result.limitations)

    def test_style_drift_when_supplied(self) -> None:
        holdings = (
            HoldingSignal(symbol="A", weight=0.9, style="growth"),
            HoldingSignal(symbol="B", weight=0.1, style="value"),
        )
        result = compute_drift_analysis(holdings)
        assert len(result.style_drift) == 3
        growth_row = next(r for r in result.style_drift if r.label == "growth")
        assert growth_row.direction is DriftDirection.OVERWEIGHT
