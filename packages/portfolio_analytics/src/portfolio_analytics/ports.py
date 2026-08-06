"""Package-local provider port — Protocol interface only.

``portfolio_analytics`` performs no I/O. Callers (``dsp_platform``) implement
this Protocol against a real data source (e.g. ``historical_series``) and
pass the resolved return series in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

from portfolio_analytics.exceptions import PortfolioAnalyticsError

__all__ = [
    "DailyReturn",
    "PriceHistoryPort",
]


@dataclass(frozen=True, slots=True)
class DailyReturn:
    """Single dated period-return observation — plain ``float``, never Decimal.

    ``portfolio_analytics`` is a statistics/simulation engine (Monte Carlo,
    covariance, random sampling); it intentionally uses ``float`` throughout,
    unlike the Decimal-only ``quantitative_risk`` ledger engine it reuses for
    Maximum Drawdown.
    """

    trade_date: date
    return_value: float

    def __post_init__(self) -> None:
        if not isinstance(self.trade_date, date):
            msg = "trade_date must be a date"
            raise PortfolioAnalyticsError(msg)
        value = float(self.return_value)
        if value != value or value in (float("inf"), float("-inf")):  # NaN/inf guard
            msg = "return_value must be a finite number"
            raise PortfolioAnalyticsError(msg)
        object.__setattr__(self, "return_value", value)


@runtime_checkable
class PriceHistoryPort(Protocol):
    """Abstract daily-return history access — no vendor/provider concepts."""

    def get_daily_returns(
        self,
        symbol: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> tuple[DailyReturn, ...] | None:
        """Return ordered (ascending date) daily returns, or ``None`` if missing."""
        ...
