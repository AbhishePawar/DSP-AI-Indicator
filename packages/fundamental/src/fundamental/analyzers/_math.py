"""Private arithmetic helpers shared by the concrete analyzers.

Financial statements routinely omit line items (``contracts.
FundamentalStatement`` models every line item beyond the identifying
fields as ``float | None``), so every ratio computed here must degrade
to ``None`` rather than raise on missing data or a zero denominator.
No analyzer duplicates this guard logic itself.
"""

from __future__ import annotations

__all__ = ["growth_rate", "safe_divide"]


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    """Divide two optional values, returning ``None`` if not computable.

    Args:
        numerator: The dividend, or ``None`` if not reported.
        denominator: The divisor, or ``None`` if not reported.

    Returns:
        ``numerator / denominator``, or ``None`` if either operand is
        ``None`` or ``denominator`` is zero.
    """
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def growth_rate(previous: float | None, latest: float | None) -> float | None:
    """Compute the fractional growth from ``previous`` to ``latest``.

    Args:
        previous: The prior period's value, or ``None`` if unavailable.
        latest: The current period's value, or ``None`` if unavailable.

    Returns:
        ``(latest - previous) / abs(previous)``, or ``None`` if either
        value is ``None`` or ``previous`` is zero.
    """
    if previous is None or latest is None or previous == 0:
        return None
    return (latest - previous) / abs(previous)
