"""portfolio_store — server-side Portfolio/Holdings/Transactions/Watchlist store.

RC1 Milestone 3. See README.md for scope (persistence only — no analytics,
no valuation; those remain exclusively ``portfolio_analytics`` and
``dsp_platform.portfolio_intelligence``).
"""

from __future__ import annotations

from portfolio_store.db_store import (
    PORTFOLIO_STORE_MIGRATIONS_SQL,
    DatabasePortfolioStore,
    build_portfolio_store,
)
from portfolio_store.exceptions import (
    ForbiddenError,
    NotFoundError,
    PortfolioStoreError,
    ValidationError,
)
from portfolio_store.models import (
    PORTFOLIO_STORE_SCHEMA_VERSION,
    PORTFOLIO_STORE_SERVICE_VERSION,
    TRANSACTION_TYPES,
    Holding,
    Portfolio,
    Transaction,
    WatchlistItem,
)
from portfolio_store.ports import PortfolioStorePort
from portfolio_store.service import (
    PortfolioService,
    get_portfolio_service,
    reset_portfolio_service_for_tests,
)
from portfolio_store.store import InMemoryPortfolioStore

__all__ = [
    "PORTFOLIO_STORE_MIGRATIONS_SQL",
    "PORTFOLIO_STORE_SCHEMA_VERSION",
    "PORTFOLIO_STORE_SERVICE_VERSION",
    "TRANSACTION_TYPES",
    "DatabasePortfolioStore",
    "ForbiddenError",
    "Holding",
    "InMemoryPortfolioStore",
    "NotFoundError",
    "Portfolio",
    "PortfolioService",
    "PortfolioStoreError",
    "PortfolioStorePort",
    "Transaction",
    "ValidationError",
    "WatchlistItem",
    "build_portfolio_store",
    "get_portfolio_service",
    "reset_portfolio_service_for_tests",
]

__version__ = "1.0.0"
