"""Portfolio persistence port — Clean Architecture boundary.

Mirrors ``enterprise.ports``.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from portfolio_store.models import Holding, Portfolio, Transaction, WatchlistItem

__all__ = ["PortfolioStorePort"]


@runtime_checkable
class PortfolioStorePort(Protocol):
    """Durable or in-memory portfolio persistence surface.

    Implementations must expose the working collections used by
    ``PortfolioService``. Tests use ``InMemoryPortfolioStore``; production
    uses ``DatabasePortfolioStore`` over a ``DatabasePort``.
    """

    portfolios: dict[str, Portfolio]
    holdings: dict[str, Holding]
    watchlist_items: dict[str, WatchlistItem]
    transactions: list[Transaction]

    def clear(self) -> None: ...

    def flush(self) -> None:
        """Persist working set when backed by durable storage (no-op in memory)."""
