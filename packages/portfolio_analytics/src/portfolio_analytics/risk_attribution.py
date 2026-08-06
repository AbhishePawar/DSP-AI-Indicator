"""Per-position risk attribution — reuses ``correlation`` for the heatmap."""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_analytics.correlation import (
    build_correlation_matrix,
    build_heatmap,
    compute_correlation,
)
from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.models import RiskAttributionProfile, RiskAttributionRow
from portfolio_analytics.ports import DailyReturn
from portfolio_analytics.returns import (
    align_return_series,
    sample_stdev,
)

__all__ = ["compute_risk_attribution"]


def compute_risk_attribution(
    *,
    weights: dict[str, float],
    sectors: dict[str, str | None],
    returns_by_symbol: dict[str, tuple[DailyReturn, ...] | None],
    portfolio_returns: Sequence[float],
    periods_per_year: int = 252,
) -> RiskAttributionProfile:
    aligned = align_return_series(returns_by_symbol)
    limitations: list[str] = []
    if aligned is None or len(aligned) < 2:
        limitations.append(
            "insufficient aligned price history across all positions; "
            "risk attribution unavailable."
        )
        return RiskAttributionProfile(
            status=AnalyticsStatus.UNAVAILABLE,
            rows=(),
            heatmap=(),
            correlation_matrix=None,
            limitations=tuple(limitations),
        )

    rows: list[RiskAttributionRow] = []
    for symbol in aligned.symbols:
        series = aligned.series[symbol]
        volatility = (
            sample_stdev(series) * (periods_per_year**0.5)
            if len(series) >= 2
            else None
        )
        correlation = compute_correlation(series, portfolio_returns)
        contribution = None
        if volatility is not None and correlation is not None:
            contribution = weights.get(symbol, 0.0) * volatility * correlation
        rows.append(
            RiskAttributionRow(
                symbol=symbol,
                weight=weights.get(symbol, 0.0),
                volatility=volatility,
                correlation_to_portfolio=correlation,
                risk_contribution_pct=contribution,
            )
        )

    total_contribution = sum(
        r.risk_contribution_pct for r in rows if r.risk_contribution_pct is not None
    )
    if total_contribution:
        rows = [
            RiskAttributionRow(
                symbol=r.symbol,
                weight=r.weight,
                volatility=r.volatility,
                correlation_to_portfolio=r.correlation_to_portfolio,
                risk_contribution_pct=(
                    r.risk_contribution_pct / total_contribution
                    if r.risk_contribution_pct is not None
                    else None
                ),
            )
            for r in rows
        ]

    heatmap = build_heatmap(
        weights=weights,
        sectors=sectors,
        aligned=aligned,
        portfolio_returns=portfolio_returns,
        periods_per_year=periods_per_year,
    )
    correlation_matrix = build_correlation_matrix(aligned)

    missing_symbols = set(returns_by_symbol) - set(aligned.symbols)
    if missing_symbols:
        limitations.append(
            f"excluded {len(missing_symbols)} position(s) with no price "
            "history: risk attribution restricted to symbols with data."
        )

    return RiskAttributionProfile(
        status=AnalyticsStatus.COMPLETE if not limitations else AnalyticsStatus.PARTIAL,
        rows=tuple(rows),
        heatmap=heatmap,
        correlation_matrix=correlation_matrix,
        limitations=tuple(limitations),
    )
