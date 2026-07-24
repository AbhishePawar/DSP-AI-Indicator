"""Tests for data_engine.normalization.coercion."""

from datetime import UTC, date, datetime

import pytest

from data_engine.exceptions import InvalidProviderDataError, MissingFieldError
from data_engine.normalization.coercion import (
    coerce_date,
    coerce_float,
    coerce_optional_float,
    coerce_timestamp,
)


class TestCoerceTimestamp:
    """Tests for coerce_timestamp."""

    def test_passes_through_timezone_aware_datetime(self) -> None:
        value = datetime(2026, 1, 2, tzinfo=UTC)
        assert coerce_timestamp(value, provider_id="fake_vendor") == value

    def test_assumes_utc_for_naive_datetime(self) -> None:
        value = datetime(2026, 1, 2)
        result = coerce_timestamp(value, provider_id="fake_vendor")
        assert result == datetime(2026, 1, 2, tzinfo=UTC)

    def test_parses_epoch_seconds(self) -> None:
        result = coerce_timestamp(1_767_312_000, provider_id="fake_vendor")
        assert result.tzinfo is not None

    def test_parses_iso_string(self) -> None:
        result = coerce_timestamp(
            "2026-01-02T00:00:00+00:00", provider_id="fake_vendor"
        )
        assert result == datetime(2026, 1, 2, tzinfo=UTC)

    def test_assumes_utc_for_naive_iso_string(self) -> None:
        result = coerce_timestamp("2026-01-02T00:00:00", provider_id="fake_vendor")
        assert result == datetime(2026, 1, 2, tzinfo=UTC)

    def test_raises_missing_field_error_for_none(self) -> None:
        with pytest.raises(MissingFieldError):
            coerce_timestamp(None, provider_id="fake_vendor")

    def test_raises_for_unparsable_string(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            coerce_timestamp("not-a-date", provider_id="fake_vendor")

    def test_raises_for_unsupported_type(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            coerce_timestamp(object(), provider_id="fake_vendor")


class TestCoerceFloat:
    """Tests for coerce_float."""

    def test_coerces_numeric_string(self) -> None:
        result = coerce_float("100.5", provider_id="fake_vendor", field_name="open")
        assert result == 100.5

    def test_coerces_int(self) -> None:
        assert coerce_float(100, provider_id="fake_vendor", field_name="open") == 100.0

    def test_raises_missing_field_error_when_required_and_none(self) -> None:
        with pytest.raises(MissingFieldError):
            coerce_float(None, provider_id="fake_vendor", field_name="volume")

    def test_returns_default_when_not_required_and_none(self) -> None:
        result = coerce_float(
            None,
            provider_id="fake_vendor",
            field_name="volume",
            required=False,
            default=0.0,
        )
        assert result == 0.0

    def test_raises_for_non_numeric_value(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            coerce_float("not-a-number", provider_id="fake_vendor", field_name="open")


class TestCoerceOptionalFloat:
    def test_returns_none_for_none(self) -> None:
        assert (
            coerce_optional_float(None, provider_id="fake", field_name="revenue")
            is None
        )

    def test_coerces_numeric(self) -> None:
        assert (
            coerce_optional_float("12.5", provider_id="fake", field_name="revenue")
            == 12.5
        )

    def test_raises_for_non_numeric(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            coerce_optional_float("x", provider_id="fake", field_name="revenue")


class TestCoerceDate:
    def test_passes_through_date(self) -> None:
        assert coerce_date(date(2024, 1, 2), provider_id="fake") == date(2024, 1, 2)

    def test_from_datetime(self) -> None:
        assert coerce_date(
            datetime(2024, 1, 2, tzinfo=UTC), provider_id="fake"
        ) == date(2024, 1, 2)

    def test_from_iso_string(self) -> None:
        assert coerce_date("2024-01-02", provider_id="fake") == date(2024, 1, 2)

    def test_from_epoch(self) -> None:
        result = coerce_date(1_704_067_200, provider_id="fake")
        assert isinstance(result, date)

    def test_none_raises(self) -> None:
        with pytest.raises(MissingFieldError):
            coerce_date(None, provider_id="fake")

    def test_bad_string_raises(self) -> None:
        with pytest.raises(InvalidProviderDataError):
            coerce_date("not-a-date", provider_id="fake")

