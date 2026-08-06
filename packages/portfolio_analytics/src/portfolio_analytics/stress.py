"""Scenario Analysis and Stress Testing.

Scenario Analysis applies a caller-defined shock (e.g. "market -20%") to
each position via its beta-implied sensitivity. Stress Testing replays a
named historical crash window using each position's *actual* historical
returns during that window when available, falling back to a beta-scaled
estimate of a supplied benchmark shock only when history is missing for
that position — the fallback usage is always counted and disclosed.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from portfolio_analytics.models import PositionInput, ScenarioImpact, StressTestResult
from portfolio_analytics.ports import DailyReturn

__all__ = [
    "compute_scenario_impact",
    "compute_stress_test",
    "cumulative_window_return",
]


def compute_scenario_impact(
    scenario_name: str,
    shock_pct: float,
    *,
    positions: Sequence[PositionInput],
    betas: dict[str, float | None] | None = None,
    default_beta: float = 1.0,
) -> ScenarioImpact:
    """Apply ``shock_pct`` to each position via beta-implied sensitivity."""
    betas = betas or {}
    per_position: dict[str, float] = {}
    weighted_sum = 0.0
    weight_total = 0.0
    for position in positions:
        beta = betas.get(position.symbol, default_beta)
        if beta is None:
            continue
        impact = shock_pct * beta
        per_position[position.symbol] = impact
        weighted_sum += position.weight * impact
        weight_total += position.weight

    portfolio_impact = weighted_sum / weight_total if weight_total > 0 else None
    return ScenarioImpact(
        scenario_name=scenario_name,
        shock_pct=shock_pct,
        portfolio_impact_pct=portfolio_impact,
        per_position_impact_pct=per_position,
    )


def cumulative_window_return(
    series: tuple[DailyReturn, ...] | None, *, window_start: date, window_end: date
) -> float | None:
    """Compound actual daily returns within ``[window_start, window_end]``.

    Public so callers (``dsp_platform``) can derive an honest benchmark shock
    for a historical crash window from the benchmark's *own* actual returns,
    rather than a fabricated constant.
    """
    if not series:
        return None
    in_window = [
        p.return_value
        for p in series
        if window_start <= p.trade_date <= window_end
    ]
    if not in_window:
        return None
    cumulative = 1.0
    for r in in_window:
        cumulative *= 1.0 + r
    return cumulative - 1.0


def compute_stress_test(
    *,
    scenario_id: str,
    description: str,
    window_start: date,
    window_end: date,
    positions: Sequence[PositionInput],
    returns_by_symbol: dict[str, tuple[DailyReturn, ...] | None],
    betas: dict[str, float | None] | None = None,
    benchmark_shock_pct: float | None = None,
) -> StressTestResult:
    betas = betas or {}
    per_position: dict[str, float] = {}
    weighted_sum = 0.0
    weight_total = 0.0
    with_history = 0
    beta_scaled = 0

    for position in positions:
        series = returns_by_symbol.get(position.symbol)
        window_return: float | None = None
        if series:
            window_return = cumulative_window_return(
                series, window_start=window_start, window_end=window_end
            )
        if window_return is not None:
            with_history += 1
        elif benchmark_shock_pct is not None:
            beta = betas.get(position.symbol)
            if beta is not None:
                window_return = benchmark_shock_pct * beta
                beta_scaled += 1

        if window_return is None:
            continue
        per_position[position.symbol] = window_return
        weighted_sum += position.weight * window_return
        weight_total += position.weight

    portfolio_return = weighted_sum / weight_total if weight_total > 0 else None
    return StressTestResult(
        scenario_id=scenario_id,
        description=description,
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        portfolio_return_pct=portfolio_return,
        per_position_return_pct=per_position,
        positions_with_history=with_history,
        positions_beta_scaled=beta_scaled,
    )
