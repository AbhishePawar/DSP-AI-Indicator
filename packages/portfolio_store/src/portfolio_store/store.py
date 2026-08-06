"""In-memory portfolio store — process-local foundation / test adapter."""

from __future__ import annotations

from threading import Lock

from portfolio_store.models import Holding, Portfolio, Transaction, WatchlistItem

__all__ = ["InMemoryPortfolioStore"]


class InMemoryPortfolioStore:
    """Thread-safe in-memory persistence for portfolio domain objects.

    Implements ``PortfolioStorePort``. Prefer ``DatabasePortfolioStore`` for
    production durability (RC1 Milestone 3), mirroring
    ``enterprise.InMemoryEnterpriseStore`` / ``DatabaseEnterpriseStore``.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self.portfolios: dict[str, Portfolio] = {}
        self.holdings: dict[str, Holding] = {}
        self.watchlist_items: dict[str, WatchlistItem] = {}
        self.transactions: list[Transaction] = []

    def clear(self) -> None:
        with self._lock:
            self.portfolios.clear()
            self.holdings.clear()
            self.watchlist_items.clear()
            self.transactions.clear()

    def flush(self) -> None:
        """No-op — in-memory adapter has no durable backend."""
