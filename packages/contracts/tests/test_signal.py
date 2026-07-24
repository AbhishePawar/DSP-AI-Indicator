"""Tests for the Signal domain contract."""

from datetime import datetime

import pytest

from contracts.domain.explanation import Explanation
from contracts.domain.instrument import Instrument
from contracts.domain.signal import Signal
from contracts.enums import EngineSource, SignalDirection
from contracts.exceptions import ContractValidationError


class TestSignal:
    """Tests for Signal construction and validation."""

    def test_minimal_signal(self, instrument: Instrument, utc_now: datetime) -> None:
        signal = Signal(
            instrument=instrument,
            source_engine=EngineSource.INDICATOR_ENGINE,
            name="rsi_14_overbought",
            direction=SignalDirection.BEARISH,
            timestamp=utc_now,
        )
        assert signal.value is None
        assert signal.strength is None
        assert signal.explanation is None

    def test_full_signal(self, instrument: Instrument, utc_now: datetime) -> None:
        explanation = Explanation(
            source_engine=EngineSource.INDICATOR_ENGINE, summary="RSI(14) = 72.4"
        )
        signal = Signal(
            instrument=instrument,
            source_engine=EngineSource.INDICATOR_ENGINE,
            name="rsi_14_overbought",
            direction=SignalDirection.BEARISH,
            timestamp=utc_now,
            value=72.4,
            strength=0.65,
            explanation=explanation,
        )
        assert signal.value == 72.4
        assert signal.strength == 0.65
        assert signal.explanation is explanation

    def test_empty_name_raises(
        self, instrument: Instrument, utc_now: datetime
    ) -> None:
        with pytest.raises(ContractValidationError, match="name"):
            Signal(
                instrument=instrument,
                source_engine=EngineSource.INDICATOR_ENGINE,
                name="",
                direction=SignalDirection.NEUTRAL,
                timestamp=utc_now,
            )

    def test_naive_timestamp_raises(self, instrument: Instrument) -> None:
        with pytest.raises(ContractValidationError, match="timezone-aware"):
            Signal(
                instrument=instrument,
                source_engine=EngineSource.INDICATOR_ENGINE,
                name="rsi_14",
                direction=SignalDirection.NEUTRAL,
                timestamp=datetime(2026, 1, 1),
            )

    def test_strength_out_of_range_raises(
        self, instrument: Instrument, utc_now: datetime
    ) -> None:
        with pytest.raises(ContractValidationError, match="strength"):
            Signal(
                instrument=instrument,
                source_engine=EngineSource.INDICATOR_ENGINE,
                name="rsi_14",
                direction=SignalDirection.NEUTRAL,
                timestamp=utc_now,
                strength=-0.1,
            )

    def test_immutable(self, instrument: Instrument, utc_now: datetime) -> None:
        signal = Signal(
            instrument=instrument,
            source_engine=EngineSource.INDICATOR_ENGINE,
            name="rsi_14",
            direction=SignalDirection.NEUTRAL,
            timestamp=utc_now,
        )
        with pytest.raises(AttributeError):
            signal.value = 50.0  # type: ignore[misc]
