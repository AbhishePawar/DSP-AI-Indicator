"""Base classes and protocols for technical indicators."""

from abc import ABC, abstractmethod

import numpy as np
import numpy.typing as npt

from core.validation import validate_period, validate_prices


class Indicator(ABC):
    """Abstract base class for all technical indicators.

    Subclasses must implement ``compute`` and define a ``name`` property.
    All indicators share consistent input validation and output shape:
    the returned array matches the input length with NaN during warmup.
    """

    def __init__(self, period: int) -> None:
        """Initialize the indicator with a lookback period.

        Args:
            period: Number of observations used in the calculation window.
        """
        self._period = validate_period(period)

    @property
    def period(self) -> int:
        """Return the configured lookback period."""
        return self._period

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the canonical indicator identifier."""

    @abstractmethod
    def compute(self, prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Compute indicator values for the given price series.

        Args:
            prices: One-dimensional sequence of price observations.

        Returns:
            Array of indicator values aligned with the input prices.
            Warmup periods are filled with NaN.
        """

    def __call__(self, prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Compute indicator values (callable shorthand).

        Args:
            prices: One-dimensional sequence of price observations.

        Returns:
            Array of indicator values aligned with the input prices.
        """
        return self.compute(prices)

    def _validate_input(self, prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
        """Validate prices and return a normalized float64 array."""
        return validate_prices(prices)
