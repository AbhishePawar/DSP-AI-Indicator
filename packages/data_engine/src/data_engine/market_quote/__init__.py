"""Authenticated market quote subsystem (EPIC-D001)."""

from __future__ import annotations

from data_engine.market_quote.adapters import (
    ConfiguredHttpQuoteAdapter,
    InMemoryAuthenticatedQuoteAdapter,
    NullAuthenticatedQuoteAdapter,
    build_default_quote_adapter_from_env,
    build_quote_from_mapping,
)
from data_engine.market_quote.models import (
    AuthenticatedMarketQuote,
    MarketQuoteProvenance,
    QuoteField,
    utc_now,
)
from data_engine.market_quote.registry import MarketQuoteProviderRegistry
from data_engine.market_quote.service import (
    CircuitBreaker,
    CircuitOpenError,
    MarketQuotePort,
    MarketQuoteService,
    MarketQuoteServiceMetrics,
    QuoteProviderHealth,
    RateLimiter,
    RetryPolicy,
)
from data_engine.market_quote.validation import validate_authenticated_quote

__all__ = [
    "AuthenticatedMarketQuote",
    "CircuitBreaker",
    "CircuitOpenError",
    "ConfiguredHttpQuoteAdapter",
    "InMemoryAuthenticatedQuoteAdapter",
    "MarketQuotePort",
    "MarketQuoteProvenance",
    "MarketQuoteProviderRegistry",
    "MarketQuoteService",
    "MarketQuoteServiceMetrics",
    "NullAuthenticatedQuoteAdapter",
    "QuoteField",
    "QuoteProviderHealth",
    "RateLimiter",
    "RetryPolicy",
    "build_default_quote_adapter_from_env",
    "build_quote_from_mapping",
    "utc_now",
    "validate_authenticated_quote",
]
