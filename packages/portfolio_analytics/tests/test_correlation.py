"""Tests for portfolio_analytics.correlation."""

from __future__ import annotations

from datetime import date

import pytest

from portfolio_analytics.correlation import (
    build_correlation_matrix,
    build_heatmap,
    compute_correlation,
)
from portfolio_analytics.ports import DailyReturn
from portfolio_analytics.returns import align_return_series


def _series(values: list[float]) -> tuple[DailyReturn, ...]:
    return tuple(
        DailyReturn(trade_date=date(2024, 1, i + 1), return_value=v)
        for i, v in enumerate(values)
    )


class TestComputeCorrelation:
    def test_self_correlation_is_one(self) -> None:
        series = [0.01, -0.02, 0.03, 0.0, 0.015]
        assert compute_correlation(series, series) == pytest.approx(1.0)

    def test_inverse_series_correlation_is_negative_one(self) -> None:
        series = [0.01, -0.02, 0.03, 0.0, 0.015]
        inverse = [-r for r in series]
        assert compute_correlation(series, inverse) == pytest.approx(-1.0)

    def test_none_on_zero_variance(self) -> None:
        assert compute_correlation([0.01, 0.01, 0.01], [0.02, 0.01, 0.0]) is None

    def test_none_on_insufficient_data(self) -> None:
        assert compute_correlation([0.01], [0.02]) is None


class TestBuildCorrelationMatrix:
    def test_diagonal_is_one(self) -> None:
        aligned = align_return_series(
            {"A": _series([0.01, 0.02, -0.01]), "B": _series([0.02, -0.01, 0.03])}
        )
        assert aligned is not None
        matrix = build_correlation_matrix(aligned)
        assert matrix is not None
        for i in range(len(matrix.symbols)):
            assert matrix.matrix[i][i] == pytest.approx(1.0)

    def test_symmetric(self) -> None:
        aligned = align_return_series(
            {"A": _series([0.01, 0.02, -0.01]), "B": _series([0.02, -0.01, 0.03])}
        )
        assert aligned is not None
        matrix = build_correlation_matrix(aligned)
        assert matrix is not None
        assert matrix.matrix[0][1] == pytest.approx(matrix.matrix[1][0])


class TestBuildHeatmap:
    def test_weights_carried_through(self) -> None:
        aligned = align_return_series(
            {"A": _series([0.01, 0.02, -0.01]), "B": _series([0.02, -0.01, 0.03])}
        )
        assert aligned is not None
        portfolio_returns = [0.015, 0.005, 0.01]
        cells = build_heatmap(
            weights={"A": 0.6, "B": 0.4},
            sectors={"A": "Tech", "B": "Energy"},
            aligned=aligned,
            portfolio_returns=portfolio_returns,
        )
        by_symbol = {c.symbol: c for c in cells}
        assert by_symbol["A"].weight == 0.6
        assert by_symbol["A"].sector == "Tech"
        assert by_symbol["B"].weight == 0.4
