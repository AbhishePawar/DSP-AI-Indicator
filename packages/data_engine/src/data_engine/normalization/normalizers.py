"""Abstract normalizer interfaces.

Each normalizer converts one category of raw model into its
corresponding ``contracts`` type. These are pure interfaces —
dependency inversion means future engines and adapters depend on these
abstractions, never on a concrete provider's normalization logic.

:class:`MarketDataNormalizer`, :class:`FundamentalNormalizer`, and
:class:`EconomicDataNormalizer` have concrete implementations today.
Alternative-data defaults remain deferred until a real provider needs them.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from contracts.domain.economic_series import EconomicSeries
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from contracts.domain.price_series import PriceSeries
from contracts.domain.signal import Signal
from data_engine.raw_models.alternative import RawAlternativeData
from data_engine.raw_models.economic import RawEconomicSeries
from data_engine.raw_models.fundamentals import RawFundamentalData
from data_engine.raw_models.market import RawMarketSeries

__all__ = [
    "AlternativeDataNormalizer",
    "EconomicDataNormalizer",
    "FundamentalNormalizer",
    "MarketDataNormalizer",
]


class MarketDataNormalizer(ABC):
    """Converts a raw, provider-specific price series into a ``PriceSeries``."""

    @abstractmethod
    def normalize(self, raw: RawMarketSeries, instrument: Instrument) -> PriceSeries:
        """Normalize raw market data into a validated ``PriceSeries``.

        Resolving instrument identity (mapping a raw ticker string to a
        proper ``Instrument``) is out of scope for a normalizer — that
        is a reference/master-data concern. Callers must already have
        the target ``Instrument`` in hand.

        Args:
            raw: The raw, unvalidated price series to normalize.
            instrument: The already-resolved instrument the series
                belongs to.

        Returns:
            A validated ``PriceSeries``.

        Raises:
            data_engine.exceptions.NormalizationError: If ``raw``
                cannot be converted into a valid ``PriceSeries``.
        """


class FundamentalNormalizer(ABC):
    """Converts raw fundamental data into a ``FundamentalStatement``."""

    @abstractmethod
    def normalize(
        self, raw: RawFundamentalData, instrument: Instrument
    ) -> FundamentalStatement:
        """Normalize raw fundamental data into a validated ``FundamentalStatement``.

        Args:
            raw: The raw, unvalidated financial statement to normalize.
            instrument: The already-resolved instrument the statement
                belongs to.

        Returns:
            A validated ``FundamentalStatement``.

        Raises:
            data_engine.exceptions.NormalizationError: If ``raw``
                cannot be converted into a valid ``FundamentalStatement``.
        """


class EconomicDataNormalizer(ABC):
    """Converts a raw, provider-specific economic series into an ``EconomicSeries``.

    Unlike market and fundamental data, economic series are not scoped
    to an ``Instrument`` — they are scoped to a country/indicator pair,
    matching ``contracts.domain.economic_series.EconomicSeries``.
    """

    @abstractmethod
    def normalize(self, raw: RawEconomicSeries) -> EconomicSeries:
        """Normalize a raw economic series into a validated ``EconomicSeries``.

        Args:
            raw: The raw, unvalidated economic series to normalize.

        Returns:
            A validated ``EconomicSeries``.

        Raises:
            data_engine.exceptions.NormalizationError: If ``raw``
                cannot be converted into a valid ``EconomicSeries``.
        """


class AlternativeDataNormalizer(ABC):
    """Converts raw, provider-specific alternative data into a ``Signal``."""

    @abstractmethod
    def normalize(self, raw: RawAlternativeData, instrument: Instrument) -> Signal:
        """Normalize raw alternative data into a validated ``Signal``.

        Args:
            raw: The raw, unvalidated alternative-data point to
                normalize.
            instrument: The already-resolved instrument the signal
                belongs to.

        Returns:
            A validated ``Signal``.

        Raises:
            data_engine.exceptions.NormalizationError: If ``raw``
                cannot be converted into a valid ``Signal``.
        """
