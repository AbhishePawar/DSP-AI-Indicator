"""Shared numeric helpers for valuation methods."""

from __future__ import annotations

from statistics import median

__all__ = ["median_or_none", "safe_divide"]


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Return ``numerator / denominator`` or ``None`` if not computable."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def median_or_none(values: list[float]) -> float | None:
    """Return the median of ``values``, or ``None`` if empty."""
    if not values:
        return None
    return float(median(values))
