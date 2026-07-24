"""Tests for DefaultEconomicNormalizer and EconomicSeriesBuilder."""

from __future__ import annotations

from datetime import date

import pytest

from contracts.domain.economic_series import EconomicDataPoint, EconomicSeries
from contracts.enums import EconomicFrequency
from data_engine.builders import EconomicSeriesBuilder
from data_engine.exceptions import InvalidProviderDataError, MissingFieldError
from data_engine.normalization import DefaultEconomicNormalizer, EconomicDataNormalizer
from data_engine.raw_models import RawEconomicDataPoint, RawEconomicSeries


def _raw(**overrides: object) -> RawEconomicSeries:
    defaults: dict[str, object] = {
        "provider_id": "fake_vendor",
        "indicator_code": "GDP",
        "country": "US",
        "frequency": "quarterly",
        "indicator_name": "Gross Domestic Product",
        "unit": "billions_of_dollars",
        "points": (
            RawEconomicDataPoint(observation_date="2023-01-01", value="100.0"),
            RawEconomicDataPoint(observation_date="2023-04-01", value="101.5"),
            RawEconomicDataPoint(observation_date="2023-07-01", value="."),
        ),
    }
    defaults.update(overrides)
    return RawEconomicSeries(**defaults)  # type: ignore[arg-type]


class TestDefaultEconomicNormalizer:
    def test_is_economic_normalizer(self) -> None:
        assert isinstance(DefaultEconomicNormalizer(), EconomicDataNormalizer)

    def test_normalizes_and_skips_missing_sentinels(self) -> None:
        series = DefaultEconomicNormalizer().normalize(_raw())
        assert series.indicator_code == "GDP"
        assert series.country == "US"
        assert series.frequency is EconomicFrequency.QUARTERLY
        assert len(series.points) == 2
        assert series.points[0].observation_date == date(2023, 1, 1)
        assert series.points[1].value == pytest.approx(101.5)

    def test_sorts_ascending_regardless_of_input_order(self) -> None:
        series = DefaultEconomicNormalizer().normalize(
            _raw(
                points=(
                    RawEconomicDataPoint("2023-04-01", 2.0),
                    RawEconomicDataPoint("2023-01-01", 1.0),
                )
            )
        )
        assert [p.observation_date for p in series.points] == [
            date(2023, 1, 1),
            date(2023, 4, 1),
        ]

    def test_deduplicates_by_date(self) -> None:
        series = DefaultEconomicNormalizer().normalize(
            _raw(
                points=(
                    RawEconomicDataPoint("2023-01-01", 1.0),
                    RawEconomicDataPoint("2023-01-01", 9.0),
                )
            )
        )
        assert len(series.points) == 1
        assert series.points[0].value == pytest.approx(9.0)

    def test_all_missing_raises(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="no usable"):
            DefaultEconomicNormalizer().normalize(
                _raw(points=(RawEconomicDataPoint("2023-01-01", "."),))
            )

    def test_missing_frequency_raises(self) -> None:
        with pytest.raises(MissingFieldError, match="frequency"):
            DefaultEconomicNormalizer().normalize(_raw(frequency=None))

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="non-numeric"):
            DefaultEconomicNormalizer().normalize(
                _raw(points=(RawEconomicDataPoint("2023-01-01", "abc"),))
            )

    def test_deterministic(self) -> None:
        normalizer = DefaultEconomicNormalizer()
        raw = _raw()
        assert normalizer.normalize(raw) == normalizer.normalize(raw)


class TestEconomicSeriesBuilder:
    def _series(self) -> EconomicSeries:
        return EconomicSeries(
            indicator_code="CPI",
            indicator_name="CPI",
            country="US",
            frequency=EconomicFrequency.MONTHLY,
            points=(
                EconomicDataPoint(date(2023, 1, 1), 100.0),
                EconomicDataPoint(date(2023, 2, 1), 101.0),
                EconomicDataPoint(date(2023, 3, 1), 102.0),
            ),
        )

    def test_limit_keeps_most_recent_ascending(self) -> None:
        result = EconomicSeriesBuilder.build(self._series(), limit=2)
        assert len(result.points) == 2
        assert result.points[0].observation_date == date(2023, 2, 1)
        assert result.points[1].observation_date == date(2023, 3, 1)

    def test_country_mismatch_raises(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="country"):
            EconomicSeriesBuilder.build(self._series(), expected_country="GB")

    def test_negative_limit_raises(self) -> None:
        with pytest.raises(InvalidProviderDataError, match="limit"):
            EconomicSeriesBuilder.build(self._series(), limit=-1)
