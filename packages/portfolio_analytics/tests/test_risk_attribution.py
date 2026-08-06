"""Tests for portfolio_analytics.risk_attribution."""

from __future__ import annotations

from datetime import date

from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.ports import DailyReturn
from portfolio_analytics.risk_attribution import compute_risk_attribution


def _series(values: list[float]) -> tuple[DailyReturn, ...]:
    return tuple(
        DailyReturn(trade_date=date(2024, 1, i + 1), return_value=v)
        for i, v in enumerate(values)
    )


class TestComputeRiskAttribution:
    def test_unavailable_when_no_history(self) -> None:
        result = compute_risk_attribution(
            weights={"AAA": 1.0},
            sectors={"AAA": "Tech"},
            returns_by_symbol={"AAA": None},
            portfolio_returns=[],
        )
        assert result.status == AnalyticsStatus.UNAVAILABLE
        assert result.rows == ()

    def test_complete_with_full_history(self) -> None:
        returns_by_symbol = {
            "AAA": _series([0.01, 0.02, -0.01, 0.03]),
            "BBB": _series([0.02, -0.01, 0.01, 0.02]),
        }
        portfolio_returns = [0.015, 0.005, 0.0, 0.025]
        result = compute_risk_attribution(
            weights={"AAA": 0.5, "BBB": 0.5},
            sectors={"AAA": "Tech", "BBB": "Energy"},
            returns_by_symbol=returns_by_symbol,
            portfolio_returns=portfolio_returns,
        )
        assert result.status == AnalyticsStatus.COMPLETE
        assert len(result.rows) == 2
        assert result.correlation_matrix is not None
        assert len(result.heatmap) == 2

    def test_unavailable_when_one_symbol_missing_history(self) -> None:
        returns_by_symbol = {
            "AAA": _series([0.01, 0.02, -0.01, 0.03]),
            "BBB": None,
        }
        result = compute_risk_attribution(
            weights={"AAA": 0.5, "BBB": 0.5},
            sectors={"AAA": "Tech", "BBB": None},
            returns_by_symbol=returns_by_symbol,
            portfolio_returns=[0.01, 0.02, -0.01, 0.03],
        )
        assert result.status == AnalyticsStatus.UNAVAILABLE
        assert result.limitations
