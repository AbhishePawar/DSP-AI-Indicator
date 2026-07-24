"""Tests for the EconomicSeries and EconomicDataPoint domain contracts."""

from datetime import date

import pytest

from contracts.domain.economic_series import EconomicDataPoint, EconomicSeries
from contracts.enums import EconomicFrequency
from contracts.exceptions import ContractValidationError


def _point(day: int, value: float) -> EconomicDataPoint:
    return EconomicDataPoint(observation_date=date(2026, 1, day), value=value)


class TestEconomicDataPoint:
    """Tests for EconomicDataPoint validation."""

    def test_valid_point(self) -> None:
        point = _point(1, 3.2)
        assert point.value == 3.2

    def test_non_finite_value_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="finite"):
            EconomicDataPoint(observation_date=date(2026, 1, 1), value=float("inf"))


class TestEconomicSeries:
    """Tests for EconomicSeries construction and ordering validation."""

    def test_valid_series(self) -> None:
        points = (_point(1, 3.0), _point(2, 3.1), _point(3, 3.2))
        series = EconomicSeries(
            indicator_code="cpi",
            indicator_name="Consumer Price Index",
            country="us",
            frequency=EconomicFrequency.MONTHLY,
            points=points,
            unit="percent",
        )
        assert series.length == 3
        assert series.indicator_code == "CPI"
        assert series.country == "US"

    def test_empty_points_raises(self) -> None:
        with pytest.raises(ContractValidationError, match="empty"):
            EconomicSeries(
                indicator_code="CPI",
                indicator_name="Consumer Price Index",
                country="US",
                frequency=EconomicFrequency.MONTHLY,
                points=(),
            )

    def test_unsorted_points_raises(self) -> None:
        points = (_point(2, 3.1), _point(1, 3.0))
        with pytest.raises(ContractValidationError, match="ascending"):
            EconomicSeries(
                indicator_code="CPI",
                indicator_name="Consumer Price Index",
                country="US",
                frequency=EconomicFrequency.MONTHLY,
                points=points,
            )

    def test_duplicate_dates_raises(self) -> None:
        points = (_point(1, 3.0), _point(1, 3.1))
        with pytest.raises(ContractValidationError, match="duplicate"):
            EconomicSeries(
                indicator_code="CPI",
                indicator_name="Consumer Price Index",
                country="US",
                frequency=EconomicFrequency.MONTHLY,
                points=points,
            )

    def test_unit_optional(self) -> None:
        series = EconomicSeries(
            indicator_code="GDP",
            indicator_name="Gross Domestic Product",
            country="US",
            frequency=EconomicFrequency.QUARTERLY,
            points=(_point(1, 2.5),),
        )
        assert series.unit is None

    def test_immutable(self) -> None:
        series = EconomicSeries(
            indicator_code="GDP",
            indicator_name="Gross Domestic Product",
            country="US",
            frequency=EconomicFrequency.QUARTERLY,
            points=(_point(1, 2.5),),
        )
        with pytest.raises(AttributeError):
            series.indicator_code = "CPI"  # type: ignore[misc]
