"""Tests for data_engine.normalization.validation."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from data_engine.exceptions import InvalidProviderDataError, MissingFieldError
from data_engine.normalization.validation import (
    DuplicateDetectionStage,
    MissingValueValidationStage,
    OHLCConsistencyStage,
    RequiredFieldValidationStage,
    SortingVerificationStage,
    TimestampValidationStage,
    ValidationPipeline,
    VolumeValidationStage,
)


@dataclass
class _Item:
    timestamp: object = None
    open: object = None
    high: object = None
    low: object = None
    close: object = None
    volume: object = None


class TestRequiredFieldValidationStage:
    """Tests for RequiredFieldValidationStage."""

    def test_passes_when_all_fields_present(self) -> None:
        stage = RequiredFieldValidationStage(field_names=("open", "close"))
        stage.validate([_Item(open=1, close=2)])

    def test_raises_missing_field_error_when_field_is_none(self) -> None:
        stage = RequiredFieldValidationStage(field_names=("open", "close"))
        with pytest.raises(MissingFieldError, match="close"):
            stage.validate([_Item(open=1, close=None)])


class TestMissingValueValidationStage:
    """Tests for MissingValueValidationStage."""

    def test_passes_for_real_values(self) -> None:
        stage = MissingValueValidationStage(field_names=("open",))
        stage.validate([_Item(open=1.0)])

    @pytest.mark.parametrize("sentinel", [None, "", "N/A", "n/a", "-"])
    def test_raises_for_default_sentinels(self, sentinel: object) -> None:
        stage = MissingValueValidationStage(field_names=("open",))
        with pytest.raises(InvalidProviderDataError):
            stage.validate([_Item(open=sentinel)])

    def test_supports_custom_sentinels(self) -> None:
        stage = MissingValueValidationStage(
            field_names=("open",), sentinels=frozenset({"null"})
        )
        with pytest.raises(InvalidProviderDataError):
            stage.validate([_Item(open="null")])


class TestTimestampValidationStage:
    """Tests for TimestampValidationStage."""

    def test_passes_for_timezone_aware_datetime(self) -> None:
        stage = TimestampValidationStage()
        stage.validate([_Item(timestamp=datetime(2026, 1, 1, tzinfo=UTC))])

    def test_raises_for_non_datetime(self) -> None:
        stage = TimestampValidationStage()
        with pytest.raises(InvalidProviderDataError, match="non-datetime"):
            stage.validate([_Item(timestamp="2026-01-01")])

    def test_raises_for_naive_datetime(self) -> None:
        stage = TimestampValidationStage()
        with pytest.raises(InvalidProviderDataError, match="timezone-naive"):
            stage.validate([_Item(timestamp=datetime(2026, 1, 1))])


class TestDuplicateDetectionStage:
    """Tests for DuplicateDetectionStage."""

    def test_passes_for_unique_keys(self) -> None:
        stage = DuplicateDetectionStage(key=lambda item: item.timestamp)
        stage.validate([_Item(timestamp=1), _Item(timestamp=2)])

    def test_raises_for_duplicate_keys(self) -> None:
        stage = DuplicateDetectionStage(key=lambda item: item.timestamp)
        with pytest.raises(InvalidProviderDataError, match="duplicate"):
            stage.validate([_Item(timestamp=1), _Item(timestamp=1)])


class TestSortingVerificationStage:
    """Tests for SortingVerificationStage."""

    def test_passes_for_ascending_order(self) -> None:
        stage = SortingVerificationStage(key=lambda item: item.timestamp)
        stage.validate([_Item(timestamp=1), _Item(timestamp=2)])

    def test_raises_for_descending_order(self) -> None:
        stage = SortingVerificationStage(key=lambda item: item.timestamp)
        with pytest.raises(InvalidProviderDataError, match="sorted"):
            stage.validate([_Item(timestamp=2), _Item(timestamp=1)])

    def test_raises_for_duplicate_keys_since_not_strictly_ascending(self) -> None:
        stage = SortingVerificationStage(key=lambda item: item.timestamp)
        with pytest.raises(InvalidProviderDataError, match="sorted"):
            stage.validate([_Item(timestamp=1), _Item(timestamp=1)])


class TestOHLCConsistencyStage:
    """Tests for OHLCConsistencyStage."""

    def test_passes_for_consistent_bar(self) -> None:
        stage = OHLCConsistencyStage()
        stage.validate([_Item(open=100.0, high=101.0, low=99.0, close=100.5)])

    def test_raises_when_low_exceeds_high(self) -> None:
        stage = OHLCConsistencyStage()
        with pytest.raises(InvalidProviderDataError, match="low"):
            stage.validate([_Item(open=100.0, high=99.0, low=101.0, close=100.0)])

    def test_raises_when_open_outside_range(self) -> None:
        stage = OHLCConsistencyStage()
        with pytest.raises(InvalidProviderDataError, match="open"):
            stage.validate([_Item(open=200.0, high=101.0, low=99.0, close=100.0)])

    def test_raises_when_close_outside_range(self) -> None:
        stage = OHLCConsistencyStage()
        with pytest.raises(InvalidProviderDataError, match="close"):
            stage.validate([_Item(open=100.0, high=101.0, low=99.0, close=200.0)])


class TestVolumeValidationStage:
    """Tests for VolumeValidationStage."""

    def test_passes_for_non_negative_volume(self) -> None:
        stage = VolumeValidationStage()
        stage.validate([_Item(volume=0.0)])

    def test_passes_when_volume_is_absent(self) -> None:
        stage = VolumeValidationStage()
        stage.validate([_Item(volume=None)])

    def test_raises_for_negative_volume(self) -> None:
        stage = VolumeValidationStage()
        with pytest.raises(InvalidProviderDataError, match="negative"):
            stage.validate([_Item(volume=-1.0)])


class TestValidationPipeline:
    """Tests for the ValidationPipeline composer."""

    def test_stops_at_first_failing_stage(self) -> None:
        calls: list[str] = []

        class _RecordingStage:
            def __init__(self, name: str, *, should_fail: bool) -> None:
                self._name = name
                self._should_fail = should_fail

            def validate(self, items: object) -> None:
                calls.append(self._name)
                if self._should_fail:
                    raise InvalidProviderDataError(self._name)

        pipeline = ValidationPipeline(
            [
                _RecordingStage("first", should_fail=True),
                _RecordingStage("second", should_fail=False),
            ]
        )
        with pytest.raises(InvalidProviderDataError, match="first"):
            pipeline.run([_Item()])
        assert calls == ["first"]

    def test_runs_all_stages_when_none_fail(self) -> None:
        pipeline = ValidationPipeline(
            [
                RequiredFieldValidationStage(field_names=("open",)),
                VolumeValidationStage(),
            ]
        )
        pipeline.run([_Item(open=1.0, volume=10.0)])
