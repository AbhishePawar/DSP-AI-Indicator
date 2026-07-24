"""Enumerations for the Data Engine provider framework.

These enumerations give the provider framework a controlled, closed
vocabulary for concepts that recur across every provider a future
adapter might integrate — Yahoo Finance, Alpha Vantage, Polygon, FMP,
Twelve Data, NSE, RBI, FRED, Quandl, CoinGecko, and any provider added
after them. None of these enumerations know about any specific vendor.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["AuthenticationType", "DataCapability", "ProviderStatus"]


class ProviderStatus(StrEnum):
    """Operational status of a registered provider.

    Used by :class:`~data_engine.providers.registry.ProviderRegistry`
    to decide which providers are eligible for automatic discovery
    (``filter_by_capability``/``select_preferred``); a provider can
    still be looked up directly by id regardless of status.
    """

    ACTIVE = "active"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class AuthenticationType(StrEnum):
    """How a provider authenticates outgoing requests.

    Descriptive only — the Data Engine does not perform authentication
    itself. A concrete adapter is responsible for actually attaching
    credentials; this enum lets that requirement be declared and
    inspected uniformly across providers.
    """

    NONE = "none"
    API_KEY = "api_key"
    OAUTH = "oauth"
    BASIC = "basic"
    TOKEN = "token"


class DataCapability(StrEnum):
    """A single, discrete kind of data a provider may be able to supply."""

    MARKET_DATA = "market_data"
    FUNDAMENTALS = "fundamentals"
    ECONOMIC_DATA = "economic_data"
    ALTERNATIVE_DATA = "alternative_data"
    INTRADAY = "intraday"
    DAILY = "daily"
    OPTIONS = "options"
    CRYPTO = "crypto"
    FOREX = "forex"
    NEWS = "news"
    ETF = "etf"
    INDICES = "indices"
    MUTUAL_FUNDS = "mutual_funds"
