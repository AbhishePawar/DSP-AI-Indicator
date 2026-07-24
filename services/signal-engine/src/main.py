"""Signal engine entry point for batch indicator computation."""

from __future__ import annotations

import numpy as np

from dsp import compute, list_indicators


def run_demo(prices: list[float] | None = None, period: int = 5) -> dict[str, list[float]]:
    """Compute all registered indicators on a sample price series.

    Args:
        prices: Optional price observations. Defaults to a sample series.
        period: Lookback window for all indicators.

    Returns:
        Dictionary mapping indicator names to computed value lists.
    """
    if prices is None:
        prices = [44.0, 44.5, 43.8, 44.2, 44.8, 45.1, 44.6, 45.3, 45.8, 46.0]

    data = np.array(prices, dtype=np.float64)
    results: dict[str, list[float]] = {}

    for name in list_indicators():
        values = compute(name, data, period)
        results[name] = [float(v) if not np.isnan(v) else None for v in values]

    return results


if __name__ == "__main__":
    output = run_demo()
    for indicator_name, values in output.items():
        print(f"{indicator_name.upper()}: {values}")
