"""Tests for core validation utilities."""

import numpy as np
import pytest

from core.exceptions import ValidationError
from core.validation import create_output_array, validate_period, validate_prices


class TestValidatePeriod:
    """Tests for validate_period."""

    def test_valid_period(self) -> None:
        assert validate_period(14) == 14

    def test_minimum_period(self) -> None:
        assert validate_period(1) == 1

    def test_zero_period_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be >= 1"):
            validate_period(0)

    def test_negative_period_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be >= 1"):
            validate_period(-5)

    def test_float_period_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_period(3.5)  # type: ignore[arg-type]

    def test_bool_period_raises(self) -> None:
        with pytest.raises(ValidationError, match="must be an integer"):
            validate_period(True)  # type: ignore[arg-type]

    def test_custom_name_in_error(self) -> None:
        with pytest.raises(ValidationError, match="window must be >= 1"):
            validate_period(0, name="window")


class TestValidatePrices:
    """Tests for validate_prices."""

    def test_valid_list(self) -> None:
        result = validate_prices([1.0, 2.0, 3.0])
        np.testing.assert_array_equal(result, [1.0, 2.0, 3.0])

    def test_valid_numpy_array(self) -> None:
        arr = np.array([10.0, 20.0], dtype=np.float64)
        result = validate_prices(arr)
        np.testing.assert_array_equal(result, arr)

    def test_converts_int_to_float64(self) -> None:
        result = validate_prices([1, 2, 3])
        assert result.dtype == np.float64

    def test_empty_raises(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            validate_prices([])

    def test_multidimensional_raises(self) -> None:
        with pytest.raises(ValidationError, match="one-dimensional"):
            validate_prices([[1.0, 2.0], [3.0, 4.0]])

    def test_nan_raises(self) -> None:
        with pytest.raises(ValidationError, match="NaN or infinite"):
            validate_prices([1.0, np.nan, 3.0])

    def test_inf_raises(self) -> None:
        with pytest.raises(ValidationError, match="NaN or infinite"):
            validate_prices([1.0, np.inf])


class TestCreateOutputArray:
    """Tests for create_output_array."""

    def test_length(self) -> None:
        result = create_output_array(5)
        assert len(result) == 5

    def test_all_nan(self) -> None:
        result = create_output_array(3)
        assert np.all(np.isnan(result))

    def test_dtype(self) -> None:
        result = create_output_array(2)
        assert result.dtype == np.float64
