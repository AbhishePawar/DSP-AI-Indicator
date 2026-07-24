"""EconomicSeries domain contract.

An :class:`EconomicSeries` is an ordered collection of observations for a
single macroeconomic indicator (e.g. CPI, GDP, the federal funds rate) over
time. It contains no interpretation of what the data means — regime
classification and trend analysis are the responsibility of the Economic
Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from contracts._validation import ensure_finite, ensure_non_empty_str
from contracts.enums import EconomicFrequency
from contracts.exceptions import ContractValidationError


@dataclass(frozen=True, slots=True)
class EconomicDataPoint:
    """A single observation within an economic data series.

    Attributes:
        observation_date: Calendar date the observation applies to.
        value: Reported value of the indicator on that date.
    """

    observation_date: date
    value: float

    def __post_init__(self) -> None:
        """Validate that the observed value is a finite number."""
        value = ensure_finite(self.value, field_name="value")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True, slots=True)
class EconomicSeries:
    """Immutable, chronologically ordered macroeconomic data series.

    Attributes:
        indicator_code: Short, provider-agnostic code for the indicator,
            normalized to uppercase (e.g. ``"CPI"``, ``"GDP"``,
            ``"FEDFUNDS"``).
        indicator_name: Human-readable name of the indicator.
        country: ISO 3166-1 alpha-2 country code the series applies to,
            normalized to uppercase.
        frequency: Observation frequency of the series.
        points: Chronologically ordered, duplicate-free observations.
        unit: Optional unit of measure (e.g. ``"percent"``, ``"index"``).
    """

    indicator_code: str
    indicator_name: str
    country: str
    frequency: EconomicFrequency
    points: tuple[EconomicDataPoint, ...]
    unit: str | None = None

    def __post_init__(self) -> None:
        """Validate identifying fields and chronological ordering of points.

        Raises:
            ContractValidationError: If ``points`` is empty, not sorted in
                strictly ascending chronological order, or contains
                duplicate observation dates.
        """
        indicator_code = ensure_non_empty_str(
            self.indicator_code, field_name="indicator_code"
        )
        indicator_code = indicator_code.strip().upper()
        country = ensure_non_empty_str(self.country, field_name="country")
        country = country.strip().upper()

        points = tuple(self.points)
        if len(points) == 0:
            msg = "points must not be empty"
            raise ContractValidationError(msg)

        dates = [point.observation_date for point in points]
        if dates != sorted(dates):
            msg = "points must be sorted in strictly ascending chronological order"
            raise ContractValidationError(msg)
        if len(set(dates)) != len(dates):
            msg = "points must not contain duplicate observation dates"
            raise ContractValidationError(msg)

        object.__setattr__(self, "indicator_code", indicator_code)
        object.__setattr__(self, "country", country)
        object.__setattr__(self, "points", points)

    @property
    def length(self) -> int:
        """Return the number of observations in the series."""
        return len(self.points)
