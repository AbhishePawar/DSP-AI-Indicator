"""Tests for the indicator registry."""

import numpy as np
import pytest

from dsp.indicators.base import Indicator
from dsp.indicators.momentum import RSI
from dsp.indicators.moving_averages import EMA, SMA, WMA
from dsp.registry import compute, get, indicator_factory, list_indicators, register


class TestRegistry:
    """Tests for indicator registration and discovery."""

    def test_list_indicators(self) -> None:
        names = list_indicators()
        assert names == ["ema", "rsi", "sma", "wma"]

    def test_get_sma(self) -> None:
        indicator = get("sma", period=5)
        assert isinstance(indicator, SMA)
        assert indicator.period == 5

    def test_get_case_insensitive(self) -> None:
        indicator = get("SMA", period=3)
        assert isinstance(indicator, SMA)

    def test_get_unknown_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown indicator"):
            get("macd", period=12)

    def test_compute_via_registry(self) -> None:
        prices = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = compute("sma", prices, period=3)
        expected = SMA(3).compute(prices)
        np.testing.assert_array_equal(result, expected)

    def test_indicator_factory(self) -> None:
        factory = indicator_factory("ema")
        indicator = factory(10)
        assert isinstance(indicator, EMA)
        assert indicator.period == 10

    def test_register_custom_indicator(self) -> None:
        register("custom_ma", SMA)
        indicator = get("custom_ma", period=2)
        assert isinstance(indicator, SMA)

    def test_register_duplicate_name_different_class_raises(self) -> None:
        class FakeIndicator(Indicator):
            @property
            def name(self) -> str:
                return "fake"

            def compute(self, prices: object) -> np.ndarray:
                return np.array([])

        with pytest.raises(ValueError, match="already registered"):
            register("sma", indicator_cls=FakeIndicator)  # type: ignore[arg-type]

    def test_all_registered_indicators_compute(self) -> None:
        prices = np.array([10.0, 11.0, 12.0, 11.5, 13.0, 12.5, 14.0])
        for name in list_indicators():
            result = compute(name, prices, period=3)
            assert len(result) == len(prices)
            assert isinstance(result, np.ndarray)

    def test_get_rsi(self) -> None:
        indicator = get("rsi", period=14)
        assert isinstance(indicator, RSI)

    def test_get_wma(self) -> None:
        indicator = get("wma", period=7)
        assert isinstance(indicator, WMA)
