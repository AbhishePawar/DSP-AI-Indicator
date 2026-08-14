"""Tests for portfolio_analytics.models — validation and public-dict shape."""

from __future__ import annotations

import pytest

from portfolio_analytics.enums import AllocationDimension, AnalyticsStatus
from portfolio_analytics.exceptions import PortfolioAnalyticsError
from portfolio_analytics.models import (
    AllocationBreakdown,
    PerformanceRatios,
    PositionInput,
)


class TestPositionInput:
    def test_normalizes_symbol_case(self) -> None:
        position = PositionInput(symbol="  aapl ", weight=0.5)
        assert position.symbol == "AAPL"

    def test_rejects_empty_symbol(self) -> None:
        with pytest.raises(PortfolioAnalyticsError):
            PositionInput(symbol="   ", weight=0.5)

    def test_rejects_negative_weight(self) -> None:
        with pytest.raises(PortfolioAnalyticsError):
            PositionInput(symbol="AAPL", weight=-0.1)

    def test_blank_sector_becomes_none(self) -> None:
        position = PositionInput(symbol="AAPL", weight=0.5, sector="  ")
        assert position.sector is None


class TestPerformanceRatiosToPublicDict:
    def test_shape(self) -> None:
        ratios = PerformanceRatios(status=AnalyticsStatus.PARTIAL, window_days=10)
        payload = ratios.to_public_dict()
        assert payload["status"] == "partial"
        assert payload["window_days"] == 10
        assert payload["sharpe_ratio"] is None


class TestAllocationBreakdownToPublicDict:
    def test_shape(self) -> None:
        breakdown = AllocationBreakdown(
            dimension=AllocationDimension.SECTOR,
            status=AnalyticsStatus.COMPLETE,
            buckets=(),
            unclassified_weight=0.0,
        )
        payload = breakdown.to_public_dict()
        assert payload["dimension"] == "sector"
        assert payload["buckets"] == []
