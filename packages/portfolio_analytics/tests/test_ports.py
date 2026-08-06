"""Tests for portfolio_analytics.ports."""

from __future__ import annotations

from datetime import date

import pytest

from portfolio_analytics.exceptions import PortfolioAnalyticsError
from portfolio_analytics.ports import DailyReturn


class TestDailyReturn:
    def test_valid_point(self) -> None:
        point = DailyReturn(trade_date=date(2024, 1, 2), return_value=0.01)
        assert point.trade_date == date(2024, 1, 2)
        assert point.return_value == 0.01

    def test_rejects_non_date(self) -> None:
        with pytest.raises(PortfolioAnalyticsError):
            DailyReturn(trade_date="2024-01-02", return_value=0.01)  # type: ignore[arg-type]

    def test_rejects_nan(self) -> None:
        with pytest.raises(PortfolioAnalyticsError):
            DailyReturn(trade_date=date(2024, 1, 2), return_value=float("nan"))

    def test_rejects_inf(self) -> None:
        with pytest.raises(PortfolioAnalyticsError):
            DailyReturn(trade_date=date(2024, 1, 2), return_value=float("inf"))
