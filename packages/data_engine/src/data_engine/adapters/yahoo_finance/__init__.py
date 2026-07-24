"""Yahoo Finance adapters (market data + fundamentals).

Sprint 2.4 delivered historical daily OHLCV via ``YahooFinanceAdapter``.
Sprint 6.2 adds as-reported financial statements via
``YahooFinanceFundamentalsAdapter``. Both reuse the same HTTP client
protocol; each remains the sole owner of its Yahoo endpoint shape.
"""

from __future__ import annotations

from data_engine.adapters.yahoo_finance.adapter import YahooFinanceAdapter
from data_engine.adapters.yahoo_finance.fundamentals_adapter import (
    YahooFinanceFundamentalsAdapter,
)
from data_engine.adapters.yahoo_finance.fundamentals_registration import (
    YAHOO_FINANCE_FUNDAMENTALS_METADATA,
    build_yahoo_finance_fundamentals_adapter,
    register_yahoo_finance_fundamentals,
)
from data_engine.adapters.yahoo_finance.http_client import (
    JsonHttpClient,
    UrllibJsonHttpClient,
)
from data_engine.adapters.yahoo_finance.registration import (
    YAHOO_FINANCE_METADATA,
    build_yahoo_finance_adapter,
    register_yahoo_finance,
)

__all__ = [
    "JsonHttpClient",
    "UrllibJsonHttpClient",
    "YAHOO_FINANCE_FUNDAMENTALS_METADATA",
    "YAHOO_FINANCE_METADATA",
    "YahooFinanceAdapter",
    "YahooFinanceFundamentalsAdapter",
    "build_yahoo_finance_adapter",
    "build_yahoo_finance_fundamentals_adapter",
    "register_yahoo_finance",
    "register_yahoo_finance_fundamentals",
]
