"""Performance ratios — Sharpe, Sortino, Treynor, Alpha, Beta, TE, IR.

Maximum Drawdown is *reused* from ``quantitative_risk.QuantitativeRiskEngine``
via its public ``calculate()`` API (see ``_max_drawdown_via_quantitative_risk``)
— never recomputed here, satisfying "no duplicate calculations".

All formulas operate on plain daily-return ``float`` sequences already
aligned to a common set of trade dates (see ``portfolio_analytics.returns``).
Every ratio is ``None`` when the inputs make it impossible to compute
honestly (fewer than 2 observations, zero benchmark variance, etc.).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.models import PerformanceRatios
from portfolio_analytics.returns import mean, sample_stdev
from quantitative_risk.engine import EngineContext, QuantitativeRiskEngine
from quantitative_risk.models import QuantitativeRiskIdentity
from quantitative_risk.ports import ReturnPoint, WeightPoint
from quantitative_risk.refs import BenchmarkReference, PortfolioReference

__all__ = [
    "compute_alpha",
    "compute_beta",
    "compute_information_ratio",
    "compute_max_drawdown_via_quantitative_risk",
    "compute_performance_ratios",
    "compute_sharpe_ratio",
    "compute_sortino_ratio",
    "compute_tracking_error",
    "compute_treynor_ratio",
]

_DEFAULT_PERIODS_PER_YEAR = 252


def _covariance(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) != len(b) or len(a) < 2:
        return None
    mean_a, mean_b = mean(a), mean(b)
    n = len(a)
    total = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    return total / (n - 1)


def compute_beta(
    portfolio_returns: Sequence[float], benchmark_returns: Sequence[float]
) -> float | None:
    """Beta = Cov(portfolio, benchmark) / Var(benchmark)."""
    cov = _covariance(portfolio_returns, benchmark_returns)
    if cov is None:
        return None
    variance = _covariance(benchmark_returns, benchmark_returns)
    if variance is None or variance == 0:
        return None
    return cov / variance


def compute_sharpe_ratio(
    returns: Sequence[float],
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: int = _DEFAULT_PERIODS_PER_YEAR,
) -> float | None:
    if len(returns) < 2:
        return None
    rf_period = risk_free_rate / periods_per_year
    excess = [r - rf_period for r in returns]
    stdev = sample_stdev(returns)
    if stdev == 0:
        return None
    return (mean(excess) / stdev) * (periods_per_year**0.5)


def compute_sortino_ratio(
    returns: Sequence[float],
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: int = _DEFAULT_PERIODS_PER_YEAR,
) -> float | None:
    if len(returns) < 2:
        return None
    rf_period = risk_free_rate / periods_per_year
    excess = [r - rf_period for r in returns]
    downside_sq = [min(e, 0.0) ** 2 for e in excess]
    downside_dev = (sum(downside_sq) / len(downside_sq)) ** 0.5
    if downside_dev == 0:
        return None
    return (mean(excess) / downside_dev) * (periods_per_year**0.5)


def compute_treynor_ratio(
    returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: int = _DEFAULT_PERIODS_PER_YEAR,
) -> float | None:
    beta = compute_beta(returns, benchmark_returns)
    if beta is None or beta == 0:
        return None
    rf_period = risk_free_rate / periods_per_year
    excess_annualized = (mean(returns) - rf_period) * periods_per_year
    return excess_annualized / beta


def compute_alpha(
    returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: int = _DEFAULT_PERIODS_PER_YEAR,
) -> float | None:
    """Jensen's Alpha, annualized: Rp - [Rf + beta * (Rm - Rf)]."""
    beta = compute_beta(returns, benchmark_returns)
    if beta is None:
        return None
    if len(returns) != len(benchmark_returns) or not returns:
        return None
    portfolio_annualized = mean(returns) * periods_per_year
    benchmark_annualized = mean(benchmark_returns) * periods_per_year
    expected = risk_free_rate + beta * (benchmark_annualized - risk_free_rate)
    return portfolio_annualized - expected


def compute_tracking_error(
    returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    periods_per_year: int = _DEFAULT_PERIODS_PER_YEAR,
) -> float | None:
    if len(returns) != len(benchmark_returns) or len(returns) < 2:
        return None
    active = [returns[i] - benchmark_returns[i] for i in range(len(returns))]
    return sample_stdev(active) * (periods_per_year**0.5)


def compute_information_ratio(
    returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    periods_per_year: int = _DEFAULT_PERIODS_PER_YEAR,
) -> float | None:
    tracking_error = compute_tracking_error(
        returns, benchmark_returns, periods_per_year=periods_per_year
    )
    if tracking_error is None or tracking_error == 0:
        return None
    if len(returns) != len(benchmark_returns) or not returns:
        return None
    active = [returns[i] - benchmark_returns[i] for i in range(len(returns))]
    active_annualized = mean(active) * periods_per_year
    return active_annualized / tracking_error


def compute_max_drawdown_via_quantitative_risk(
    returns: Sequence[float],
) -> float | None:
    """Reuse ``quantitative_risk.QuantitativeRiskEngine`` for Maximum Drawdown.

    Builds minimal in-process port implementations around the caller's
    already-fetched float return series and drives the frozen engine's
    public ``calculate()`` method — never reimplements the drawdown formula.
    """
    if not returns:
        return None

    class _SingleWeight:
        def get_portfolio_weights(
            self, portfolio_id: str, *, as_of: str, snapshot_id: str | None = None
        ) -> tuple[WeightPoint, ...] | None:
            return (WeightPoint(instrument_id="portfolio", weight=Decimal("1")),)

    class _ReturnsAdapter:
        def get_returns(
            self, series_id: str, *, window_id: str
        ) -> tuple[ReturnPoint, ...] | None:
            return tuple(
                ReturnPoint(timestamp=str(i), value=Decimal(str(r)))
                for i, r in enumerate(returns)
            )

    context = EngineContext(
        identity=QuantitativeRiskIdentity(
            quantitative_risk_id="portfolio-analytics-drawdown-shim",
            quantitative_risk_name="portfolio_analytics max drawdown reuse",
        ),
        portfolio_ref=PortfolioReference(portfolio_id="portfolio-analytics"),
        market_data=_SingleWeight(),
        historical_returns=_ReturnsAdapter(),
        benchmark_data=_ReturnsAdapter(),
        benchmark_ref=BenchmarkReference(benchmark_id="portfolio-analytics-benchmark"),
        window_id="portfolio-analytics-window",
        as_of="portfolio-analytics-as-of",
    )
    result = QuantitativeRiskEngine().calculate(context)
    if not result.drawdowns:
        return None
    return float(result.drawdowns[0].max_drawdown)


def compute_performance_ratios(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float] | None,
    *,
    risk_free_rate: float = 0.0,
    periods_per_year: int = _DEFAULT_PERIODS_PER_YEAR,
) -> PerformanceRatios:
    """Compute the full performance panel; every field honestly-empty on gaps."""
    limitations: list[str] = []
    window_days = len(portfolio_returns)

    max_drawdown = compute_max_drawdown_via_quantitative_risk(portfolio_returns)
    sharpe = compute_sharpe_ratio(
        portfolio_returns,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )
    sortino = compute_sortino_ratio(
        portfolio_returns,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
    )
    annualized_return = (
        mean(portfolio_returns) * periods_per_year if portfolio_returns else None
    )
    annualized_volatility = (
        sample_stdev(portfolio_returns) * (periods_per_year**0.5)
        if len(portfolio_returns) >= 2
        else None
    )

    beta = treynor = alpha = tracking_error = information_ratio = None
    if benchmark_returns is None:
        limitations.append(
            "benchmark_symbol not supplied or benchmark history unavailable; "
            "beta/alpha/treynor/tracking_error/information_ratio unavailable."
        )
    else:
        beta = compute_beta(portfolio_returns, benchmark_returns)
        treynor = compute_treynor_ratio(
            portfolio_returns,
            benchmark_returns,
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year,
        )
        alpha = compute_alpha(
            portfolio_returns,
            benchmark_returns,
            risk_free_rate=risk_free_rate,
            periods_per_year=periods_per_year,
        )
        tracking_error = compute_tracking_error(
            portfolio_returns, benchmark_returns, periods_per_year=periods_per_year
        )
        information_ratio = compute_information_ratio(
            portfolio_returns, benchmark_returns, periods_per_year=periods_per_year
        )

    if window_days < 2:
        limitations.append(
            "fewer than 2 aligned return observations; most ratios unavailable."
        )

    computed = [
        v
        for v in (
            sharpe,
            sortino,
            treynor,
            alpha,
            beta,
            tracking_error,
            information_ratio,
            max_drawdown,
        )
        if v is not None
    ]
    if not computed:
        status = AnalyticsStatus.UNAVAILABLE
    elif len(computed) < 8:
        status = AnalyticsStatus.PARTIAL
    else:
        status = AnalyticsStatus.COMPLETE

    return PerformanceRatios(
        status=status,
        window_days=window_days,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        treynor_ratio=treynor,
        jensen_alpha=alpha,
        beta=beta,
        tracking_error=tracking_error,
        information_ratio=information_ratio,
        max_drawdown=max_drawdown,
        annualized_return=annualized_return,
        annualized_volatility=annualized_volatility,
        risk_free_rate=risk_free_rate,
        limitations=tuple(limitations),
    )
