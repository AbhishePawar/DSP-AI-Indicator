"""Request models for the orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from contracts.domain.instrument import Instrument
from contracts.enums import BarFrequency, StatementPeriodType
from orchestration.exceptions import OrchestrationError

__all__ = ["AnalysisRequest"]


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    """Immutable request for a full-platform investment analysis.

    Attributes:
        instrument: Already-resolved instrument to analyze.
        start: Inclusive start date for market data.
        end: Inclusive end date for market data (also default ``as_of``
            for economic snapshots when series are sparse).
        market_frequency: Bar frequency for price history.
        statement_period: Annual / quarterly / TTM for fundamentals.
        fundamentals_limit: Max statement periods (most recent first).
        economic_country: ISO country for macroeconomic series.
        include_fundamentals: When ``False``, skip fundamentals and
            omit the Fundamental committee member.
        include_economic: When ``False``, skip economics and omit the
            Economic committee member.
        include_valuation: When ``False``, skip valuation and omit the
            Valuation committee member.
        allow_partial: When ``True``, a failed optional stage (fundamentals,
            economics, or valuation) is skipped instead of aborting the
            pipeline. Market data and DSP analysis remain mandatory.
        market_provider: Optional market-data provider id override.
        fundamentals_provider: Optional fundamentals provider id override.
        economic_provider: Optional economic provider id override.
        market_cap: Optional equity market capitalization override for
            Margin of Safety. When omitted, orchestration reads
            ``market_capitalization`` from fundamental extras.
    """

    instrument: Instrument
    start: date
    end: date
    market_frequency: BarFrequency = BarFrequency.DAILY
    statement_period: StatementPeriodType = StatementPeriodType.ANNUAL
    fundamentals_limit: int | None = 4
    economic_country: str = "US"
    include_fundamentals: bool = True
    include_economic: bool = True
    include_valuation: bool = True
    allow_partial: bool = True
    market_provider: str | None = None
    fundamentals_provider: str | None = None
    economic_provider: str | None = None
    market_cap: float | None = None

    def __post_init__(self) -> None:
        """Validate date range and limit."""
        if self.start > self.end:
            msg = f"start ({self.start}) must not be after end ({self.end})"
            raise OrchestrationError(msg)
        if self.fundamentals_limit is not None and self.fundamentals_limit < 0:
            msg = f"fundamentals_limit must be non-negative, got {self.fundamentals_limit}"
            raise OrchestrationError(msg)
        if not self.economic_country.strip():
            msg = "economic_country must not be empty"
            raise OrchestrationError(msg)
        if self.market_cap is not None and self.market_cap < 0:
            msg = f"market_cap must be non-negative, got {self.market_cap}"
            raise OrchestrationError(msg)
