"""Input validation utilities for indicator computation."""

import numpy as np
import numpy.typing as npt

from core.exceptions import ValidationError


def validate_period(period: int, *, name: str = "period") -> int:
    """Validate that a lookback period is a positive integer.

    Args:
        period: Number of observations in the lookback window.
        name: Parameter name used in error messages.

    Returns:
        The validated period value.

    Raises:
        ValidationError: If period is not a positive integer.
    """
    if not isinstance(period, int) or isinstance(period, bool):
        msg = f"{name} must be an integer, got {type(period).__name__}"
        raise ValidationError(msg)
    if period < 1:
        msg = f"{name} must be >= 1, got {period}"
        raise ValidationError(msg)
    return period


def validate_prices(prices: npt.ArrayLike) -> npt.NDArray[np.float64]:
    """Validate and normalize a one-dimensional price array.

    Args:
        prices: Raw price observations.

    Returns:
        A float64 numpy array of prices.

    Raises:
        ValidationError: If prices are empty or not one-dimensional.
    """
    array = np.asarray(prices, dtype=np.float64)
    if array.ndim != 1:
        msg = f"prices must be one-dimensional, got {array.ndim} dimensions"
        raise ValidationError(msg)
    if array.size == 0:
        msg = "prices must not be empty"
        raise ValidationError(msg)
    if not np.all(np.isfinite(array)):
        msg = "prices must not contain NaN or infinite values"
        raise ValidationError(msg)
    return array


def create_output_array(length: int) -> npt.NDArray[np.float64]:
    """Create a float64 output array pre-filled with NaN.

    Args:
        length: Number of elements in the output array.

    Returns:
        An array of the given length filled with NaN.
    """
    return np.full(length, np.nan, dtype=np.float64)
