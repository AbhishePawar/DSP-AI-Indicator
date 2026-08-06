"""Monte Carlo simulation and Efficient Frontier sampling.

Both are explicitly documented, seedable approximations — never presented as
exact optimization or forecasting. Monte Carlo bootstrap-resamples the
supplied historical daily-return series (no distributional assumption);
Efficient Frontier randomly samples portfolio weight vectors over the
historical covariance structure implied by the same aligned return series
and keeps only the non-dominated (Pareto-efficient) points.
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from portfolio_analytics.enums import AnalyticsStatus
from portfolio_analytics.models import (
    EfficientFrontierPoint,
    EfficientFrontierResult,
    MonteCarloSummary,
)
from portfolio_analytics.returns import (
    AlignedReturns,
    mean,
    sample_stdev,
    weighted_series,
)

__all__ = [
    "compute_efficient_frontier",
    "compute_monte_carlo",
]

_MONTE_CARLO_METHOD_ID = "dsp.portfolio_analytics.method.monte_carlo.bootstrap.v1"
_FRONTIER_METHOD_ID = (
    "dsp.portfolio_analytics.method.efficient_frontier.random_weight_sampling.v1"
)


def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    rank = pct / 100 * (len(sorted_values) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    frac = rank - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * frac


def compute_monte_carlo(
    portfolio_returns: Sequence[float],
    *,
    paths: int = 1000,
    horizon_days: int = 252,
    seed: int | None = None,
) -> MonteCarloSummary:
    """Bootstrap-resample ``portfolio_returns`` to simulate terminal outcomes."""
    if len(portfolio_returns) < 2 or paths < 1 or horizon_days < 1:
        return MonteCarloSummary(
            status=AnalyticsStatus.UNAVAILABLE,
            paths=paths,
            horizon_days=horizon_days,
            method_id=_MONTE_CARLO_METHOD_ID,
            seed=seed,
            limitations=(
                "fewer than 2 historical daily returns available; Monte "
                "Carlo simulation unavailable.",
            ),
        )

    rng = random.Random(seed)
    history = list(portfolio_returns)
    terminal_returns: list[float] = []
    for _ in range(paths):
        cumulative = 1.0
        for _day in range(horizon_days):
            cumulative *= 1.0 + rng.choice(history)
        terminal_returns.append(cumulative - 1.0)

    terminal_returns.sort()
    percentiles = {
        "p5": _percentile(terminal_returns, 5),
        "p25": _percentile(terminal_returns, 25),
        "p50": _percentile(terminal_returns, 50),
        "p75": _percentile(terminal_returns, 75),
        "p95": _percentile(terminal_returns, 95),
    }
    return MonteCarloSummary(
        status=AnalyticsStatus.COMPLETE,
        paths=paths,
        horizon_days=horizon_days,
        percentiles=percentiles,
        mean_terminal_return=mean(terminal_returns),
        method_id=_MONTE_CARLO_METHOD_ID,
        seed=seed,
        limitations=(
            "Bootstrap resampling of historical daily returns — an "
            "approximation that assumes future returns are drawn from the "
            "same historical distribution; not a probabilistic guarantee.",
        ),
    )


def _random_weights(rng: random.Random, n: int) -> tuple[float, ...]:
    raw = [rng.random() for _ in range(n)]
    total = sum(raw) or 1.0
    return tuple(r / total for r in raw)


def _pareto_frontier(
    points: list[EfficientFrontierPoint],
) -> tuple[EfficientFrontierPoint, ...]:
    """Keep only points with no other point that is both higher-return and
    lower-or-equal volatility (standard efficient-frontier non-domination)."""
    frontier: list[EfficientFrontierPoint] = []
    for candidate in points:
        dominated = any(
            other is not candidate
            and other.expected_return >= candidate.expected_return
            and other.volatility <= candidate.volatility
            and (
                other.expected_return > candidate.expected_return
                or other.volatility < candidate.volatility
            )
            for other in points
        )
        if not dominated:
            frontier.append(candidate)
    frontier.sort(key=lambda p: p.volatility)
    return tuple(frontier)


def compute_efficient_frontier(
    aligned: AlignedReturns,
    *,
    current_weights: dict[str, float] | None = None,
    samples: int = 200,
    seed: int | None = None,
    periods_per_year: int = 252,
) -> EfficientFrontierResult:
    symbols = aligned.symbols
    if len(symbols) < 2 or len(aligned) < 2:
        return EfficientFrontierResult(
            status=AnalyticsStatus.UNAVAILABLE,
            points=(),
            current_portfolio_point=None,
            method_id=_FRONTIER_METHOD_ID,
            samples=samples,
            limitations=(
                "efficient frontier requires at least 2 positions with at "
                "least 2 aligned historical return observations each.",
            ),
        )

    rng = random.Random(seed)
    sampled_points: list[EfficientFrontierPoint] = []
    for _ in range(samples):
        weights = dict(zip(symbols, _random_weights(rng, len(symbols)), strict=True))
        series = weighted_series(weights, aligned)
        if series is None:
            continue
        expected_return = mean(series) * periods_per_year
        volatility = sample_stdev(series) * (periods_per_year**0.5)
        sampled_points.append(
            EfficientFrontierPoint(
                expected_return=expected_return, volatility=volatility, weights=weights
            )
        )

    frontier = _pareto_frontier(sampled_points)

    current_point: EfficientFrontierPoint | None = None
    if current_weights:
        series = weighted_series(current_weights, aligned)
        if series is not None:
            current_point = EfficientFrontierPoint(
                expected_return=mean(series) * periods_per_year,
                volatility=sample_stdev(series) * (periods_per_year**0.5),
                weights=dict(current_weights),
            )

    return EfficientFrontierResult(
        status=AnalyticsStatus.COMPLETE if frontier else AnalyticsStatus.UNAVAILABLE,
        points=frontier,
        current_portfolio_point=current_point,
        method_id=_FRONTIER_METHOD_ID,
        samples=samples,
        limitations=(
            "Mean-variance random-weight sampling over historical returns — "
            "an approximation, not a closed-form quadratic optimization; "
            "results depend on the sampled weight vectors and history window.",
        ),
    )
