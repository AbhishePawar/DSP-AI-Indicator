"""Tests for momentum indicators."""

import numpy as np
import pytest

from core.exceptions import ValidationError
from dsp.indicators.momentum import RSI, rsi


class TestRSI:
    """Tests for Relative Strength Index."""

    def test_name(self) -> None:
        assert RSI(14).name == "rsi"

    def test_default_period(self) -> None:
        indicator = RSI(14)
        assert indicator.period == 14

    def test_known_values(self) -> None:
        prices = np.array([100.0, 102.0, 101.0, 105.0, 104.0])
        result = RSI(3).compute(prices)
        expected = [np.nan, np.nan, np.nan, 600.0 / 7.0, 100.0 / 1.4]
        # Last value: 100 - 100/(1 + 2.4) = 100/3.4
        expected[-1] = 100.0 - 100.0 / 3.4
        np.testing.assert_array_almost_equal(result, expected, decimal=3)

    def test_overbought_on_monotonic_up(self, monotonic_up: np.ndarray) -> None:
        result = RSI(3).compute(monotonic_up)
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 50.0)

    def test_oversold_on_monotonic_down(self, monotonic_down: np.ndarray) -> None:
        result = RSI(3).compute(monotonic_down)
        valid = result[~np.isnan(result)]
        assert np.all(valid <= 50.0)

    def test_constant_prices(self, constant_prices: np.ndarray) -> None:
        result = RSI(3).compute(constant_prices)
        valid = result[~np.isnan(result)]
        np.testing.assert_array_almost_equal(valid, [0.0, 0.0])

    def test_all_gains_returns_100(self) -> None:
        prices = np.array([10.0, 11.0, 12.0, 13.0, 14.0])
        result = RSI(2).compute(prices)
        valid = result[~np.isnan(result)]
        np.testing.assert_array_almost_equal(valid, [100.0, 100.0, 100.0])

    def test_insufficient_data_all_nan(self) -> None:
        result = RSI(14).compute([1.0, 2.0, 3.0])
        assert np.all(np.isnan(result))

    def test_output_length_matches_input(self, sample_prices: np.ndarray) -> None:
        result = rsi(sample_prices, period=5)
        assert len(result) == len(sample_prices)

    def test_warmup_nan_count(self, sample_prices: np.ndarray) -> None:
        period = 5
        result = rsi(sample_prices, period=period)
        assert np.all(np.isnan(result[:period]))
        assert not np.any(np.isnan(result[period:]))

    def test_values_bounded_0_100(self, sample_prices: np.ndarray) -> None:
        result = RSI(5).compute(sample_prices)
        valid = result[~np.isnan(result)]
        assert np.all(valid >= 0.0)
        assert np.all(valid <= 100.0)

    def test_function_shorthand_matches_class(self, sample_prices: np.ndarray) -> None:
        np.testing.assert_array_equal(
            rsi(sample_prices, 5),
            RSI(5).compute(sample_prices),
        )

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValidationError):
            RSI(0)

    def test_empty_prices_raises(self) -> None:
        with pytest.raises(ValidationError):
            RSI(14).compute([])

    def test_callable_shorthand(self, sample_prices: np.ndarray) -> None:
        indicator = RSI(5)
        np.testing.assert_array_equal(indicator(sample_prices), indicator.compute(sample_prices))
