"""Internal request models for the Data Engine.

These types describe the Data Engine's own internal request shapes. They
intentionally do not duplicate anything in ``contracts`` — any type that
represents platform domain data (a price, a statement, a signal) is a
Contracts type, not a Data Engine model. What lives here is operational:
how a caller asks this engine's services for that data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import BarFrequency, StatementPeriodType
from data_engine.exceptions import DataEngineError

__all__ = ["EconomicRequest", "FundamentalsRequest", "PriceSeriesRequest"]



@dataclass(frozen=True, slots=True)
class PriceSeriesRequest:
    """A single, immutable request for a price series.

    Attributes:
        instrument: The instrument to retrieve prices for.
        frequency: Sampling frequency of the requested bars.
        start: Inclusive start date of the requested range.
        end: Inclusive end date of the requested range.
        provider_name: Optional explicit provider to query; when omitted,
            the requesting service falls back to its configured default.
    """

    instrument: Instrument
    frequency: BarFrequency
    start: date
    end: date
    provider_name: str | None = None

    def __post_init__(self) -> None:
        """Validate that the requested date range is well-formed.

        Raises:
            DataEngineError: If ``start`` is after ``end``.
        """
        if self.start > self.end:
            msg = f"start ({self.start}) must not be after end ({self.end})"
            raise DataEngineError(msg)


@dataclass(frozen=True, slots=True)
class FundamentalsRequest:
    """A single, immutable request for fundamental statements.

    Attributes:
        instrument: The instrument to retrieve statements for.
        period_type: Annual, quarterly, or trailing-twelve-month.
        limit: Optional maximum number of most-recent periods.
        provider_name: Optional explicit provider to query; when omitted,
            the requesting service falls back to its configured default.
    """

    instrument: Instrument
    period_type: StatementPeriodType
    limit: int | None = None
    provider_name: str | None = None

    def __post_init__(self) -> None:
        """Validate that ``limit`` is well-formed when provided.

        Raises:
            DataEngineError: If ``limit`` is negative.
        """
        if self.limit is not None and self.limit < 0:
            msg = f"limit must be non-negative, got {self.limit}"
            raise DataEngineError(msg)


@dataclass(frozen=True, slots=True)
class EconomicRequest:
    """A single, immutable request for a macroeconomic series.

    Attributes:
        indicator_code: Provider-agnostic indicator code (e.g. ``"GDP"``).
        country: ISO 3166-1 alpha-2 country code.
        limit: Optional maximum number of most-recent observations.
        provider_name: Optional explicit provider to query; when omitted,
            the requesting service falls back to its configured default.
    """

    indicator_code: str
    country: str
    limit: int | None = None
    provider_name: str | None = None

    def __post_init__(self) -> None:
        """Validate identifying fields and ``limit``.

        Raises:
            DataEngineError: If ``indicator_code``/``country`` is empty
                or ``limit`` is negative.
        """
        if not self.indicator_code.strip():
            msg = "indicator_code must not be empty"
            raise DataEngineError(msg)
        if not self.country.strip():
            msg = "country must not be empty"
            raise DataEngineError(msg)
        if self.limit is not None and self.limit < 0:
            msg = f"limit must be non-negative, got {self.limit}"
            raise DataEngineError(msg)
