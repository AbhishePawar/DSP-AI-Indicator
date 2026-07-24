"""Momentum-based indicator implementations."""

import numpy as np
import numpy.typing as npt

from core.validation import create_output_array
from dsp.indicators.base import Indicator


class RSI(Indicator):
    """Relative Strength Index (RSI) using Wilder's smoothing method.

    Measures the magnitude of recent price changes to evaluate overbought
    or oversold conditions. Values range from 0 to 100.
    """

    @property
    def name(self) -> str:
        """Return the indicator identifier."""
        return "rsi"

    def compute(self, prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Compute RSI values for the given price series.

        Args:
            prices: One-dimensional sequence of price observations.

        Returns:
            RSI values (0–100) with NaN during the warmup window.
        """
        data = self._validate_input(prices)
        output = create_output_array(len(data))

        if len(data) < self.period + 1:
            return output

        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = np.mean(gains[: self.period])
        avg_loss = np.mean(losses[: self.period])

        output[self.period] = self._calc_rsi(avg_gain, avg_loss)

        for idx in range(self.period + 1, len(data)):
            delta_idx = idx - 1
            avg_gain = (avg_gain * (self.period - 1) + gains[delta_idx]) / self.period
            avg_loss = (avg_loss * (self.period - 1) + losses[delta_idx]) / self.period
            output[idx] = self._calc_rsi(avg_gain, avg_loss)

        return output

    @staticmethod
    def _calc_rsi(avg_gain: float, avg_loss: float) -> float:
        """Convert average gain/loss into an RSI value.

        Args:
            avg_gain: Smoothed average of positive price changes.
            avg_loss: Smoothed average of negative price changes.

        Returns:
            RSI value between 0 and 100.
        """
        if avg_loss == 0.0:
            return 100.0 if avg_gain > 0.0 else 0.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))


def rsi(prices: npt.ArrayLike, period: int = 14) -> npt.NDArray[np.float64]:
    """Compute Relative Strength Index.

    Args:
        prices: One-dimensional price observations.
        period: Lookback window size (default 14).

    Returns:
        RSI values aligned with the input prices.
    """
    return RSI(period).compute(prices)
