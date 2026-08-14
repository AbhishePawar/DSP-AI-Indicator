"""Abstract ports for external data sources consumed by the Data Engine.

A port defines *what* the Data Engine can ask an external data source for,
never *how* that source is queried. Concrete integrations (a specific
market-data vendor, a specific fundamentals API, and so on) implement
these interfaces as adapters in ``data_engine.adapters`` — this module
never imports a concrete adapter, and no adapter is implemented here.

This is the dependency-inversion boundary required by Clean Architecture:
the Data Engine's own application logic (``data_engine.services``)
depends only on these abstract ports, never on a specific vendor's SDK or
API client. External providers must be reached only through a port,
implemented by an adapter, and looked up through the provider registry.

Ports are currently synchronous. See ``packages/data_engine/README.md``
("Design Decisions") for the rationale and the future migration path to
asynchronous I/O once a real, network-calling adapter exists.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from contracts.domain.economic_series import EconomicSeries
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.domain.signal import Signal
from contracts.enums import BarFrequency, StatementPeriodType

from data_engine.market_quote.service import MarketQuotePort as MarketQuotePort
from data_engine.financial_statement.service import (
    FinancialStatementPort as FinancialStatementPort,
)
from data_engine.corporate_actions.service import (
    CorporateActionPort as CorporateActionPort,
)
from data_engine.historical_series.service import (
    HistoricalSeriesPort as HistoricalSeriesPort,
)

__all__ = [
    "AlternativeDataPort",
    "CorporateActionPort",
    "EconomicDataPort",
    "FinancialStatementPort",
    "FundamentalsDataPort",
    "HistoricalSeriesPort",
    "MarketDataPort",
    "MarketQuotePort",
]


class MarketDataPort(ABC):
    """Port for retrieving price history for an instrument."""

    @abstractmethod
    def get_price_series(
        self,
        instrument: Instrument,
        frequency: BarFrequency,
        start: date,
        end: date,
    ) -> PriceSeries:
        """Retrieve a price series for an instrument over a date range.

        Args:
            instrument: The instrument to retrieve prices for.
            frequency: Sampling frequency of the requested bars.
            start: Inclusive start date of the requested range.
            end: Inclusive end date of the requested range.

        Returns:
            A validated price series covering the requested range.
        """


class FundamentalsDataPort(ABC):
    """Port for retrieving financial statements for an instrument."""

    @abstractmethod
    def get_fundamental_statements(
        self,
        instrument: Instrument,
        period_type: StatementPeriodType,
        *,
        limit: int | None = None,
    ) -> tuple[FundamentalStatement, ...]:
        """Retrieve financial statements for an instrument.

        Args:
            instrument: The instrument to retrieve statements for.
            period_type: Whether to retrieve annual, quarterly, or TTM
                statements.
            limit: Optional maximum number of most-recent periods to
                retrieve. ``None`` means no limit.

        Returns:
            Financial statements ordered from most recent to oldest.
        """


class EconomicDataPort(ABC):
    """Port for retrieving macroeconomic data series."""

    @abstractmethod
    def get_economic_series(self, indicator_code: str, country: str) -> EconomicSeries:
        """Retrieve an economic data series.

        Args:
            indicator_code: Provider-agnostic code for the indicator
                (e.g. ``"CPI"``, ``"GDP"``).
            country: ISO 3166-1 alpha-2 country code.

        Returns:
            The requested economic data series.
        """


class AlternativeDataPort(ABC):
    """Port for retrieving alternative/behavioral data signals."""

    @abstractmethod
    def get_signals(self, instrument: Instrument) -> tuple[Signal, ...]:
        """Retrieve alternative-data signals for an instrument.

        Args:
            instrument: The instrument to retrieve signals for.

        Returns:
            Signals derived from alternative data sources (e.g. sentiment,
            positioning) for the given instrument.
        """
