"""Tests for portfolio_analytics.returns alignment helpers."""

from __future__ import annotations

from datetime import date

import pytest

from portfolio_analytics.ports import DailyReturn
from portfolio_analytics.returns import (
    align_return_series,
    mean,
    sample_stdev,
    weighted_series,
)


def _series(values: dict[str, float]) -> tuple[DailyReturn, ...]:
    return tuple(
        DailyReturn(trade_date=date(2024, 1, day), return_value=value)
        for day, value in values.items()
    )


class TestAlignReturnSeries:
    def test_none_when_any_symbol_missing(self) -> None:
        aligned = align_return_series({"AAA": None, "BBB": _series({1: 0.01})})
        assert aligned is None

    def test_none_when_no_overlap(self) -> None:
        a = (DailyReturn(trade_date=date(2024, 1, 1), return_value=0.01),)
        b = (DailyReturn(trade_date=date(2024, 2, 1), return_value=0.02),)
        assert align_return_series({"A": a, "B": b}) is None

    def test_intersects_common_dates(self) -> None:
        a = (
            DailyReturn(trade_date=date(2024, 1, 1), return_value=0.01),
            DailyReturn(trade_date=date(2024, 1, 2), return_value=0.02),
        )
        b = (
            DailyReturn(trade_date=date(2024, 1, 2), return_value=0.03),
            DailyReturn(trade_date=date(2024, 1, 3), return_value=0.04),
        )
        aligned = align_return_series({"A": a, "B": b})
        assert aligned is not None
        assert aligned.dates == (date(2024, 1, 2),)
        assert aligned.series["A"] == (0.02,)
        assert aligned.series["B"] == (0.03,)


class TestWeightedSeries:
    def test_weighted_blend(self) -> None:
        a = (DailyReturn(trade_date=date(2024, 1, 1), return_value=0.10),)
        b = (DailyReturn(trade_date=date(2024, 1, 1), return_value=0.20),)
        aligned = align_return_series({"A": a, "B": b})
        assert aligned is not None
        blended = weighted_series({"A": 0.5, "B": 0.5}, aligned)
        assert blended is not None
        assert blended[0] == pytest.approx(0.15)

    def test_none_when_zero_total_weight(self) -> None:
        a = (DailyReturn(trade_date=date(2024, 1, 1), return_value=0.10),)
        aligned = align_return_series({"A": a})
        assert aligned is not None
        assert weighted_series({"A": 0.0}, aligned) is None

    def test_renormalizes_partial_weights(self) -> None:
        a = (DailyReturn(trade_date=date(2024, 1, 1), return_value=0.10),)
        b = (DailyReturn(trade_date=date(2024, 1, 1), return_value=0.30),)
        aligned = align_return_series({"A": a, "B": b})
        assert aligned is not None
        # Only A has nonzero weight among symbols present -> result is A's value.
        blended = weighted_series({"A": 1.0, "B": 0.0}, aligned)
        assert blended == (0.10,)


class TestStats:
    def test_mean_empty(self) -> None:
        assert mean([]) == 0.0

    def test_sample_stdev_single_value(self) -> None:
        assert sample_stdev([0.5]) == 0.0

    def test_sample_stdev_known(self) -> None:
        # values 1,2,3 -> mean 2, variance = ((1)+(0)+(1))/2 = 1 -> stdev 1
        assert sample_stdev([1.0, 2.0, 3.0]) == 1.0
