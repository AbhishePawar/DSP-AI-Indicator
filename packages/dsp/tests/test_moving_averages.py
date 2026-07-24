"""Tests for moving average indicators."""

import numpy as np
import pytest

from core.exceptions import ValidationError
from dsp.indicators.moving_averages import EMA, SMA, WMA, ema, sma, wma


class TestSMA:
    """Tests for Simple Moving Average."""

    def test_name(self) -> None:
        assert SMA(5).name == "sma"

    def test_known_values(self, simple_prices: np.ndarray) -> None:
        result = SMA(3).compute(simple_prices)
        expected = [np.nan, np.nan, 2.0, 3.0, 4.0]
        np.testing.assert_array_almost_equal(result, expected)

    def test_period_one_returns_input(self, simple_prices: np.ndarray) -> None:
        result = SMA(1).compute(simple_prices)
        np.testing.assert_array_equal(result, simple_prices)

    def test_insufficient_data_all_nan(self) -> None:
        result = SMA(5).compute([1.0, 2.0, 3.0])
        assert np.all(np.isnan(result))

    def test_output_length_matches_input(self, sample_prices: np.ndarray) -> None:
        result = sma(sample_prices, period=5)
        assert len(result) == len(sample_prices)

    def test_warmup_nan_count(self, sample_prices: np.ndarray) -> None:
        period = 5
        result = sma(sample_prices, period=period)
        assert np.all(np.isnan(result[: period - 1]))
        assert not np.any(np.isnan(result[period - 1 :]))

    def test_constant_prices(self, constant_prices: np.ndarray) -> None:
        result = SMA(3).compute(constant_prices)
        valid = result[~np.isnan(result)]
        np.testing.assert_array_almost_equal(valid, [50.0, 50.0, 50.0])

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValidationError):
            SMA(0)

    def test_empty_prices_raises(self) -> None:
        with pytest.raises(ValidationError):
            SMA(3).compute([])

    def test_function_shorthand_matches_class(self, simple_prices: np.ndarray) -> None:
        np.testing.assert_array_equal(sma(simple_prices, 3), SMA(3).compute(simple_prices))

    def test_accepts_python_list(self) -> None:
        result = sma([10.0, 20.0, 30.0, 40.0], period=2)
        assert not np.isnan(result[-1])


class TestEMA:
    """Tests for Exponential Moving Average."""

    def test_name(self) -> None:
        assert EMA(5).name == "ema"

    def test_known_values(self, simple_prices: np.ndarray) -> None:
        result = EMA(3).compute(simple_prices)
        expected = [np.nan, np.nan, 2.0, 3.0, 4.0]
        np.testing.assert_array_almost_equal(result, expected)

    def test_period_one_returns_input(self, simple_prices: np.ndarray) -> None:
        result = EMA(1).compute(simple_prices)
        np.testing.assert_array_equal(result, simple_prices)

    def test_insufficient_data_all_nan(self) -> None:
        result = EMA(5).compute([1.0, 2.0])
        assert np.all(np.isnan(result))

    def test_responds_to_recent_prices(self, monotonic_up: np.ndarray) -> None:
        result = EMA(3).compute(monotonic_up)
        valid = result[~np.isnan(result)]
        assert valid[-1] > valid[0]

    def test_output_length_matches_input(self, sample_prices: np.ndarray) -> None:
        result = ema(sample_prices, period=5)
        assert len(result) == len(sample_prices)

    def test_function_shorthand_matches_class(self, simple_prices: np.ndarray) -> None:
        np.testing.assert_array_equal(ema(simple_prices, 3), EMA(3).compute(simple_prices))

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValidationError):
            EMA(-1)


class TestWMA:
    """Tests for Weighted Moving Average."""

    def test_name(self) -> None:
        assert WMA(5).name == "wma"

    def test_known_values(self, simple_prices: np.ndarray) -> None:
        result = WMA(3).compute(simple_prices)
        expected = [np.nan, np.nan, 14.0 / 6.0, 20.0 / 6.0, 26.0 / 6.0]
        np.testing.assert_array_almost_equal(result, expected)

    def test_period_one_returns_input(self, simple_prices: np.ndarray) -> None:
        result = WMA(1).compute(simple_prices)
        np.testing.assert_array_equal(result, simple_prices)

    def test_weights_favor_recent_prices(self) -> None:
        """WMA of rising series should exceed SMA at the same period."""
        prices = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        wma_result = WMA(3).compute(prices)
        sma_result = SMA(3).compute(prices)
        assert wma_result[-1] > sma_result[-1]

    def test_insufficient_data_all_nan(self) -> None:
        result = WMA(4).compute([1.0, 2.0])
        assert np.all(np.isnan(result))

    def test_output_length_matches_input(self, sample_prices: np.ndarray) -> None:
        result = wma(sample_prices, period=5)
        assert len(result) == len(sample_prices)

    def test_function_shorthand_matches_class(self, simple_prices: np.ndarray) -> None:
        np.testing.assert_array_equal(wma(simple_prices, 3), WMA(3).compute(simple_prices))

    def test_constant_prices(self, constant_prices: np.ndarray) -> None:
        result = WMA(3).compute(constant_prices)
        valid = result[~np.isnan(result)]
        np.testing.assert_array_almost_equal(valid, [50.0, 50.0, 50.0])

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValidationError):
            WMA(0)
