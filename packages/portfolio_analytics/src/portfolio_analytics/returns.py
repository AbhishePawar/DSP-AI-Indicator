"""Shared return-series alignment helpers.

Used by ``performance``, ``correlation``, ``risk_attribution``, ``simulation``,
and ``stress`` to combine per-symbol daily returns into a portfolio-level
series on a common (inner-joined) set of trade dates. Never fabricates a
value for a missing date — dates without full coverage are simply excluded.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from portfolio_analytics.ports import DailyReturn

__all__ = [
    "AlignedReturns",
    "align_return_series",
    "weighted_series",
]


class AlignedReturns:
    """Common ascending dates + per-symbol return arrays aligned to them."""

    __slots__ = ("dates", "series")

    def __init__(self, dates: tuple[date, ...], series: dict[str, tuple[float, ...]]):
        self.dates = dates
        self.series = series

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(self.series.keys())

    def __len__(self) -> int:
        return len(self.dates)


def align_return_series(
    series_by_symbol: Mapping[str, tuple[DailyReturn, ...] | None],
) -> AlignedReturns | None:
    """Inner-join every symbol's returns onto their common trade dates.

    Returns ``None`` when any symbol has no history, or there is no overlap.
    """
    usable = {
        symbol: series
        for symbol, series in series_by_symbol.items()
        if series
    }
    if not usable or len(usable) != len(series_by_symbol):
        return None

    date_sets = [
        {point.trade_date for point in series} for series in usable.values()
    ]
    common = set.intersection(*date_sets) if date_sets else set()
    if not common:
        return None

    common_sorted = tuple(sorted(common))
    aligned: dict[str, tuple[float, ...]] = {}
    for symbol, series in usable.items():
        by_date = {point.trade_date: point.return_value for point in series}
        aligned[symbol] = tuple(by_date[d] for d in common_sorted)
    return AlignedReturns(dates=common_sorted, series=aligned)


def weighted_series(
    weights: Mapping[str, float], aligned: AlignedReturns
) -> tuple[float, ...] | None:
    """Weight-blend aligned per-symbol series into one portfolio return series.

    Weights are renormalized across the symbols present in ``aligned`` so a
    partial-coverage portfolio still sums to 1.0 among the symbols actually
    contributing. Returns ``None`` when total weight is zero.
    """
    symbols = aligned.symbols
    total_weight = sum(max(weights.get(s, 0.0), 0.0) for s in symbols)
    if total_weight <= 0:
        return None

    n = len(aligned)
    out: list[float] = []
    for i in range(n):
        acc = 0.0
        for symbol in symbols:
            w = max(weights.get(symbol, 0.0), 0.0)
            acc += w * aligned.series[symbol][i]
        out.append(acc / total_weight)
    return tuple(out)


def mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def sample_stdev(values: Sequence[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    avg = mean(values)
    variance = sum((v - avg) ** 2 for v in values) / (n - 1)
    return variance**0.5
