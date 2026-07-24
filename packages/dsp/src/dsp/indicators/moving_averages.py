"""Moving average indicator implementations."""

import numpy as np
import numpy.typing as npt

from core.validation import create_output_array
from dsp.indicators.base import Indicator


class SMA(Indicator):
    """Simple Moving Average (SMA).

    Computes the arithmetic mean of the last ``period`` prices at each point.
    The first ``period - 1`` values in the output are NaN.
    """

    @property
    def name(self) -> str:
        """Return the indicator identifier."""
        return "sma"

    def compute(self, prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Compute SMA values for the given price series.

        Args:
            prices: One-dimensional sequence of price observations.

        Returns:
            SMA values with NaN during the warmup window.
        """
        data = self._validate_input(prices)
        output = create_output_array(len(data))

        if self.period == 1:
            return data.copy()

        if len(data) < self.period:
            return output

        kernel = np.ones(self.period, dtype=np.float64) / self.period
        convolved = np.convolve(data, kernel, mode="valid")
        output[self.period - 1 :] = convolved
        return output


class EMA(Indicator):
    """Exponential Moving Average (EMA).

    Uses smoothing factor ``alpha = 2 / (period + 1)``. The first EMA value
    is seeded with the SMA of the initial ``period`` observations.
    """

    @property
    def name(self) -> str:
        """Return the indicator identifier."""
        return "ema"

    def compute(self, prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Compute EMA values for the given price series.

        Args:
            prices: One-dimensional sequence of price observations.

        Returns:
            EMA values with NaN during the warmup window.
        """
        data = self._validate_input(prices)
        output = create_output_array(len(data))

        if self.period == 1:
            return data.copy()

        if len(data) < self.period:
            return output

        alpha = 2.0 / (self.period + 1)
        seed = np.mean(data[: self.period])
        output[self.period - 1] = seed

        for idx in range(self.period, len(data)):
            prev = output[idx - 1]
            output[idx] = alpha * data[idx] + (1.0 - alpha) * prev

        return output


class WMA(Indicator):
    """Weighted Moving Average (WMA).

    Applies linearly increasing weights (1, 2, ..., period) to the most
    recent prices within each window. More recent prices receive higher weight.
    """

    @property
    def name(self) -> str:
        """Return the indicator identifier."""
        return "wma"

    def compute(self, prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Compute WMA values for the given price series.

        Args:
            prices: One-dimensional sequence of price observations.

        Returns:
            WMA values with NaN during the warmup window.
        """
        data = self._validate_input(prices)
        output = create_output_array(len(data))

        if self.period == 1:
            return data.copy()

        if len(data) < self.period:
            return output

        weights = np.arange(1, self.period + 1, dtype=np.float64)
        weight_sum = weights.sum()

        for idx in range(self.period - 1, len(data)):
            window = data[idx - self.period + 1 : idx + 1]
            output[idx] = np.dot(window, weights) / weight_sum

        return output


def sma(prices: npt.ArrayLike, period: int) -> npt.NDArray[np.float64]:
    """Compute Simple Moving Average.

    Args:
        prices: One-dimensional price observations.
        period: Lookback window size.

    Returns:
        SMA values aligned with the input prices.
    """
    return SMA(period).compute(prices)


def ema(prices: npt.ArrayLike, period: int) -> npt.NDArray[np.float64]:
    """Compute Exponential Moving Average.

    Args:
        prices: One-dimensional price observations.
        period: Lookback window size.

    Returns:
        EMA values aligned with the input prices.
    """
    return EMA(period).compute(prices)


def wma(prices: npt.ArrayLike, period: int) -> npt.NDArray[np.float64]:
    """Compute Weighted Moving Average.

    Args:
        prices: One-dimensional price observations.
        period: Lookback window size.

    Returns:
        WMA values aligned with the input prices.
    """
    return WMA(period).compute(prices)
