"""``PriceHistoryPort`` implementation backed by ``historical_series`` (EPIC-D004).

Wraps ``dsp_platform.historical_series.get_authenticated_historical_series`` —
reused, not reimplemented. No new provider integration; the resilience
(cache/retry/circuit-breaker) already lives in that façade.
"""

from __future__ import annotations

from datetime import date

from portfolio_analytics.ports import DailyReturn, PriceHistoryPort

__all__ = ["HistoricalSeriesPriceHistoryAdapter"]

_DEFAULT_LOOKBACK_BARS = 750


class HistoricalSeriesPriceHistoryAdapter(PriceHistoryPort):
    """Derives daily returns from authenticated OHLCV close prices."""

    def __init__(self, *, lookback_bars: int = _DEFAULT_LOOKBACK_BARS) -> None:
        self._lookback_bars = lookback_bars

    def get_daily_returns(
        self,
        symbol: str,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> tuple[DailyReturn, ...] | None:
        from dsp_platform.historical_series import get_authenticated_historical_series

        payload = get_authenticated_historical_series(
            symbol,
            series_kind="ohlcv",
            frequency="daily",
            end_date=end,
            limit=self._lookback_bars,
        )
        if payload is None:
            return None
        bars = payload.get("bars") or []
        closes: list[tuple[date, float]] = []
        for bar in bars:
            close = bar.get("close")
            bar_date = bar.get("date")
            if close is None or bar_date is None:
                continue
            try:
                closes.append((date.fromisoformat(str(bar_date)[:10]), float(close)))
            except (ValueError, TypeError):
                continue
        if len(closes) < 2:
            return None

        closes.sort(key=lambda pair: pair[0])
        returns: list[DailyReturn] = []
        for i in range(1, len(closes)):
            prev_date, prev_close = closes[i - 1]
            cur_date, cur_close = closes[i]
            if prev_close == 0:
                continue
            if start is not None and cur_date < start:
                continue
            returns.append(
                DailyReturn(
                    trade_date=cur_date,
                    return_value=(cur_close - prev_close) / prev_close,
                )
            )
        if not returns:
            return None
        return tuple(returns)
