"""Derivation helpers for projecting EconomicSeries into EconomicSnapshot fields."""

from __future__ import annotations

from datetime import date, timedelta

from contracts.domain.economic_series import EconomicDataPoint, EconomicSeries

__all__ = [
    "latest_as_of",
    "normalize_liquidity",
    "percent_level_to_decimal",
    "period_change",
    "yoy_growth",
]


def latest_as_of(series_list: list[EconomicSeries]) -> date | None:
    """Return the latest observation date across all series, if any."""
    dates: list[date] = []
    for series in series_list:
        if series.points:
            dates.append(series.points[-1].observation_date)
    return max(dates) if dates else None


def _find_prior(
    points: tuple[EconomicDataPoint, ...],
    *,
    anchor: date,
    target_delta_days: int,
    tolerance_days: int,
) -> EconomicDataPoint | None:
    """Find the observation nearest to ``anchor - target_delta_days``."""
    target = anchor - timedelta(days=target_delta_days)
    best: EconomicDataPoint | None = None
    best_distance = tolerance_days + 1
    for point in points:
        distance = abs((point.observation_date - target).days)
        if distance <= tolerance_days and distance < best_distance:
            best = point
            best_distance = distance
    return best


def yoy_growth(series: EconomicSeries | None) -> float | None:
    """Year-over-year growth of the latest level as a decimal fraction.

    Uses a ±45-day window around the date one year prior so monthly and
    quarterly series both resolve. Returns ``None`` when fewer than two
    usable points exist or the prior level is zero.
    """
    if series is None or len(series.points) < 2:
        return None
    latest = series.points[-1]
    prior = _find_prior(
        series.points,
        anchor=latest.observation_date,
        target_delta_days=365,
        tolerance_days=45,
    )
    if prior is None or prior.value == 0.0:
        return None
    return (latest.value - prior.value) / abs(prior.value)


def period_change(series: EconomicSeries | None) -> float | None:
    """Change between the two most recent observations (raw units)."""
    if series is None or len(series.points) < 2:
        return None
    return series.points[-1].value - series.points[-2].value


def percent_level_to_decimal(value: float | None) -> float | None:
    """Convert a percent-scale level (e.g. ``5.33``) to a decimal (``0.0533``).

    FRED interest-rate and unemployment series report percent units.
    Values already in ``(-1, 1)`` excluding zero extremes are treated as
    decimals and returned unchanged; values with ``abs >= 1`` are divided
    by 100. ``None`` stays ``None``.
    """
    if value is None:
        return None
    if abs(value) < 1.0:
        return value
    return value / 100.0


def normalize_liquidity(m2_series: EconomicSeries | None) -> float | None:
    """Map M2 year-over-year growth onto a ``[0.0, 1.0]`` liquidity score.

    Linear map of YoY growth from ``-2%`` → ``0.0`` to ``+12%`` → ``1.0``,
    clipped to the unit interval. Missing M2 data yields ``None``.
    """
    growth = yoy_growth(m2_series)
    if growth is None:
        return None
    # growth of -0.02 → 0.0; +0.12 → 1.0
    score = (growth + 0.02) / 0.14
    return max(0.0, min(1.0, score))
