"""Position Limits and Rebalancing.

Both are explicitly framed as *analysis*, never a trade/order instruction —
consistent with the rest of the platform's compliance language (see
``RebalancingPlan.disclaimer``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from portfolio_analytics.enums import AnalyticsStatus, RebalancingAction
from portfolio_analytics.models import (
    PositionInput,
    PositionLimitBreach,
    PositionLimitReport,
    RebalancingPlan,
    RebalancingTrade,
)

__all__ = [
    "check_position_limits",
    "compute_rebalancing_plan",
]


def check_position_limits(
    positions: Sequence[PositionInput],
    *,
    max_position_weight: float | None = None,
    max_sector_weight: float | None = None,
    sector_limits: Mapping[str, float] | None = None,
    min_cash_weight: float | None = None,
    cash_weight: float | None = None,
) -> PositionLimitReport:
    checks: list[PositionLimitBreach] = []
    sector_limits = sector_limits or {}

    if max_position_weight is not None:
        for position in positions:
            checks.append(
                PositionLimitBreach(
                    label=position.symbol,
                    limit_type="max_position_weight",
                    limit_value=max_position_weight,
                    actual_value=position.weight,
                    breached=position.weight > max_position_weight,
                )
            )

    if max_sector_weight is not None or sector_limits:
        sector_totals: dict[str, float] = {}
        for position in positions:
            if position.sector is None:
                continue
            sector_totals[position.sector] = (
                sector_totals.get(position.sector, 0.0) + position.weight
            )
        for sector, total in sector_totals.items():
            limit = sector_limits.get(sector, max_sector_weight)
            if limit is None:
                continue
            checks.append(
                PositionLimitBreach(
                    label=sector,
                    limit_type="max_sector_weight",
                    limit_value=limit,
                    actual_value=total,
                    breached=total > limit,
                )
            )

    if min_cash_weight is not None and cash_weight is not None:
        checks.append(
            PositionLimitBreach(
                label="cash",
                limit_type="min_cash_weight",
                limit_value=min_cash_weight,
                actual_value=cash_weight,
                breached=cash_weight < min_cash_weight,
            )
        )

    breaches = tuple(c for c in checks if c.breached)
    status = AnalyticsStatus.COMPLETE if checks else AnalyticsStatus.UNAVAILABLE
    return PositionLimitReport(status=status, breaches=breaches, checks=tuple(checks))


def compute_rebalancing_plan(
    positions: Sequence[PositionInput],
    target_weights: Mapping[str, float],
    *,
    drift_threshold: float = 0.0,
) -> RebalancingPlan:
    """Compare current vs. target weights — analysis only, never a trade order."""
    if not target_weights:
        return RebalancingPlan(status=AnalyticsStatus.UNAVAILABLE, trades=(), total_drift=0.0)

    current_by_symbol = {p.symbol: p.weight for p in positions}
    symbols = set(current_by_symbol) | set(target_weights)
    trades: list[RebalancingTrade] = []
    total_drift = 0.0

    for symbol in sorted(symbols):
        current = current_by_symbol.get(symbol, 0.0)
        target = target_weights.get(symbol, 0.0)
        drift = current - target
        total_drift += abs(drift)
        if drift > drift_threshold:
            action = RebalancingAction.DECREASE
        elif drift < -drift_threshold:
            action = RebalancingAction.INCREASE
        else:
            action = RebalancingAction.HOLD
        trades.append(
            RebalancingTrade(
                symbol=symbol,
                current_weight=current,
                target_weight=target,
                drift=drift,
                suggested_action=action,
                suggested_delta_weight=target - current,
            )
        )

    return RebalancingPlan(
        status=AnalyticsStatus.COMPLETE, trades=tuple(trades), total_drift=total_drift
    )
