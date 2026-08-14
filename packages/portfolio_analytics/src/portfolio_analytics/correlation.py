"""Correlation matrix and portfolio heatmap."""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_analytics.models import CorrelationMatrix, HeatmapCell
from portfolio_analytics.returns import AlignedReturns, sample_stdev

__all__ = [
    "build_correlation_matrix",
    "build_heatmap",
    "compute_correlation",
]


def compute_correlation(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    std_a, std_b = sample_stdev(a), sample_stdev(b)
    if std_a == 0 or std_b == 0:
        return None
    mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
    n = len(a)
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n)) / (n - 1)
    return cov / (std_a * std_b)


def build_correlation_matrix(aligned: AlignedReturns) -> CorrelationMatrix | None:
    """Pairwise correlation matrix across every symbol in ``aligned``."""
    symbols = aligned.symbols
    if len(symbols) < 1:
        return None
    matrix: list[tuple[float | None, ...]] = []
    for row_symbol in symbols:
        row: list[float | None] = []
        for col_symbol in symbols:
            if row_symbol == col_symbol:
                row.append(1.0 if len(aligned) >= 1 else None)
            else:
                row.append(
                    compute_correlation(
                        aligned.series[row_symbol], aligned.series[col_symbol]
                    )
                )
        matrix.append(tuple(row))
    return CorrelationMatrix(
        symbols=symbols, matrix=tuple(matrix), window_days=len(aligned)
    )


def build_heatmap(
    *,
    weights: dict[str, float],
    sectors: dict[str, str | None],
    aligned: AlignedReturns,
    portfolio_returns: Sequence[float],
    periods_per_year: int = 252,
) -> tuple[HeatmapCell, ...]:
    """Per-symbol weight x volatility x correlation-to-portfolio risk contribution."""
    cells: list[HeatmapCell] = []
    contributions: dict[str, float | None] = {}
    for symbol in aligned.symbols:
        series = aligned.series[symbol]
        volatility = (
            sample_stdev(series) * (periods_per_year**0.5)
            if len(series) >= 2
            else None
        )
        correlation = compute_correlation(series, portfolio_returns)
        weight = weights.get(symbol, 0.0)
        contribution = None
        if volatility is not None and correlation is not None:
            contribution = weight * volatility * correlation
        contributions[symbol] = contribution

    total = sum(c for c in contributions.values() if c is not None)
    for symbol in aligned.symbols:
        contribution = contributions[symbol]
        risk_pct = None
        if contribution is not None and total not in (0, None):
            risk_pct = contribution / total
        series = aligned.series[symbol]
        volatility = (
            sample_stdev(series) * (periods_per_year**0.5)
            if len(series) >= 2
            else None
        )
        cells.append(
            HeatmapCell(
                symbol=symbol,
                sector=sectors.get(symbol),
                weight=weights.get(symbol, 0.0),
                volatility=volatility,
                risk_contribution_pct=risk_pct,
            )
        )
    return tuple(cells)
