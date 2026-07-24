"""Tests for dsp.engine.models (IndicatorSpec, IndicatorResult)."""

from datetime import UTC, datetime

import pytest

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, BarFrequency
from core.exceptions import ValidationError
from dsp.engine.models import IndicatorResult, IndicatorSpec


class TestIndicatorSpec:
    """Tests for IndicatorSpec normalization and validation."""

    def test_normalizes_name_to_lowercase(self) -> None:
        spec = IndicatorSpec("RSI", 14)
        assert spec.name == "rsi"

    def test_strips_whitespace_from_name(self) -> None:
        spec = IndicatorSpec("  ema  ", 12)
        assert spec.name == "ema"

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValidationError):
            IndicatorSpec("   ", 14)

    def test_invalid_period_raises(self) -> None:
        with pytest.raises(ValidationError):
            IndicatorSpec("rsi", 0)

    def test_is_frozen(self) -> None:
        spec = IndicatorSpec("rsi", 14)
        with pytest.raises(AttributeError):
            spec.period = 21  # type: ignore[misc]


class TestIndicatorResult:
    """Tests for IndicatorResult's label and immutability."""

    def _make_result(self) -> IndicatorResult:
        instrument = Instrument(
            symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
        )
        now = datetime(2024, 1, 5, tzinfo=UTC)
        return IndicatorResult(
            instrument=instrument,
            name="rsi",
            period=14,
            frequency=BarFrequency.DAILY,
            source_values=(100.0, 101.0, 102.0),
            values=(float("nan"), float("nan"), 76.2),
            latest_value=76.2,
            as_of=now,
            computed_at=now,
        )

    def test_label_formats_name_and_period(self) -> None:
        result = self._make_result()
        assert result.label == "RSI(14)"

    def test_is_frozen(self) -> None:
        result = self._make_result()
        with pytest.raises(AttributeError):
            result.latest_value = 50.0  # type: ignore[misc]
