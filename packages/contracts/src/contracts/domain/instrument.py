"""Instrument domain contract.

An :class:`Instrument` uniquely identifies a tradable security or index and
carries the classification metadata every other engine needs in order to
interpret data about it correctly. It contains no market data, no
fundamentals, and no computed metrics — only identity and classification.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts._validation import ensure_non_empty_str
from contracts.enums import AssetClass
from contracts.exceptions import ContractValidationError


@dataclass(frozen=True, slots=True)
class Instrument:
    """Immutable identifier and classification for a tradable instrument.

    Attributes:
        symbol: Primary trading symbol/ticker, normalized to uppercase
            (e.g. ``"AAPL"``).
        asset_class: Broad classification of the instrument.
        currency: ISO 4217 currency code the instrument is quoted in,
            normalized to uppercase (e.g. ``"USD"``).
        name: Optional full display name (e.g. ``"Apple Inc."``).
        exchange: Optional exchange or venue identifier (e.g. ``"NASDAQ"``).
        sector: Optional sector classification (e.g. ``"Technology"``).
        industry: Optional industry classification, more granular than
            ``sector`` (e.g. ``"Consumer Electronics"``).
        country: Optional ISO 3166-1 alpha-2 country code of primary
            listing (e.g. ``"US"``).
        isin: Optional International Securities Identification Number.
        figi: Optional Financial Instrument Global Identifier.
    """

    symbol: str
    asset_class: AssetClass
    currency: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    isin: str | None = None
    figi: str | None = None

    def __post_init__(self) -> None:
        """Normalize and validate identifying fields."""
        symbol = ensure_non_empty_str(self.symbol, field_name="symbol")
        symbol = symbol.strip().upper()
        currency = ensure_non_empty_str(self.currency, field_name="currency")
        currency = currency.strip().upper()
        if len(currency) != 3:
            msg = f"currency must be a 3-letter ISO 4217 code, got {currency!r}"
            raise ContractValidationError(msg)

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "currency", currency)
