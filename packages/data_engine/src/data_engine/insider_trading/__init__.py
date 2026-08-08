"""Authenticated insider trading (Data Connector Framework)."""

from __future__ import annotations

from data_engine.insider_trading.adapters import (
    BseInsiderTradingAdapter,
    FinancialModelingPrepInsiderTradingAdapter,
    InMemoryInsiderTradingAdapter,
    NseInsiderTradingAdapter,
    NullInsiderTradingAdapter,
    SecEdgarInsiderTradingAdapter,
    YahooFinanceInsiderTradingAdapter,
    build_default_insider_trading_registry_from_env,
    build_insider_activity_from_mapping,
)
from data_engine.insider_trading.models import (
    INSIDER_TRANSACTION_TYPES,
    AuthenticatedInsiderActivity,
    InsiderTransaction,
)
from data_engine.insider_trading.registry import InsiderTradingProviderRegistry
from data_engine.insider_trading.service import (
    InsiderTradingProviderPort,
    InsiderTradingQuery,
    InsiderTradingService,
    InsiderTradingServiceMetrics,
)
from data_engine.insider_trading.validation import validate_authenticated_insider_activity

__all__ = [
    "INSIDER_TRANSACTION_TYPES",
    "AuthenticatedInsiderActivity",
    "BseInsiderTradingAdapter",
    "FinancialModelingPrepInsiderTradingAdapter",
    "InMemoryInsiderTradingAdapter",
    "InsiderTradingProviderPort",
    "InsiderTradingProviderRegistry",
    "InsiderTradingQuery",
    "InsiderTradingService",
    "InsiderTradingServiceMetrics",
    "InsiderTransaction",
    "NseInsiderTradingAdapter",
    "NullInsiderTradingAdapter",
    "SecEdgarInsiderTradingAdapter",
    "YahooFinanceInsiderTradingAdapter",
    "build_default_insider_trading_registry_from_env",
    "build_insider_activity_from_mapping",
    "validate_authenticated_insider_activity",
]
