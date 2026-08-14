"""Durability tests for portfolio_store.db_store.DatabasePortfolioStore.

Mirrors packages/enterprise/tests/test_epic016_commercial_ga.py's
rehydrate-after-restart pattern exactly.
"""

from __future__ import annotations

from portfolio_store.db_store import DatabasePortfolioStore, build_portfolio_store
from portfolio_store.service import PortfolioService
from portfolio_store.store import InMemoryPortfolioStore
from production_platform import InMemoryDatabasePort


class TestBuildPortfolioStore:
    def test_returns_in_memory_when_no_database(self) -> None:
        store = build_portfolio_store()
        assert isinstance(store, InMemoryPortfolioStore)
        assert not isinstance(store, DatabasePortfolioStore)

    def test_returns_database_backed_when_database_supplied(self) -> None:
        db = InMemoryDatabasePort()
        store = build_portfolio_store(db)
        assert isinstance(store, DatabasePortfolioStore)


class TestDatabasePortfolioStoreDurability:
    def test_survives_rehydrate_across_service_instances(self) -> None:
        db = InMemoryDatabasePort()
        svc = PortfolioService(store=DatabasePortfolioStore(db))
        portfolio = svc.create_portfolio(
            user_id="u1", name="Durable Portfolio", benchmark_symbol="SPY"
        )
        pid = portfolio["portfolio_id"]
        svc.upsert_holding(pid, user_id="u1", symbol="AAPL", weight=0.6, sector="Tech")
        svc.add_watchlist_symbol(pid, user_id="u1", symbol="NVDA")
        svc.record_transaction(
            pid,
            user_id="u1",
            transaction_type="buy",
            transaction_date="2024-01-01",
            symbol="AAPL",
            quantity=10,
            price=150,
        )

        # New service instance, same underlying DatabasePort — simulates a
        # process restart with the same durable backend.
        reloaded = PortfolioService(store=DatabasePortfolioStore(db))
        restored = reloaded.get_portfolio(pid, user_id="u1")
        assert restored["name"] == "Durable Portfolio"
        assert restored["benchmark_symbol"] == "SPY"
        assert restored["is_default"] is True

        holdings = reloaded.list_holdings(pid, user_id="u1")
        assert len(holdings) == 1
        assert holdings[0]["symbol"] == "AAPL"

        watchlist = reloaded.list_watchlist(pid, user_id="u1")
        assert watchlist[0]["symbol"] == "NVDA"

        transactions = reloaded.list_transactions(pid, user_id="u1")
        assert len(transactions) == 1
        assert transactions[0]["transaction_type"] == "buy"

    def test_transactions_are_append_only_and_never_overwritten(self) -> None:
        db = InMemoryDatabasePort()
        svc = PortfolioService(store=DatabasePortfolioStore(db))
        portfolio = svc.create_portfolio(user_id="u1", name="P")
        pid = portfolio["portfolio_id"]
        svc.record_transaction(
            pid, user_id="u1", transaction_type="buy",
            transaction_date="2024-01-01", symbol="AAPL", quantity=1, price=100,
        )
        svc.record_transaction(
            pid, user_id="u1", transaction_type="sell",
            transaction_date="2024-02-01", symbol="AAPL", quantity=1, price=110,
        )

        store2 = DatabasePortfolioStore(db)
        types = sorted(t.transaction_type for t in store2.transactions)
        assert types == ["buy", "sell"]

    def test_multiple_portfolios_persist_independently(self) -> None:
        db = InMemoryDatabasePort()
        svc = PortfolioService(store=DatabasePortfolioStore(db))
        p1 = svc.create_portfolio(user_id="u1", name="First")
        p2 = svc.create_portfolio(user_id="u1", name="Second")
        svc.upsert_holding(p1["portfolio_id"], user_id="u1", symbol="AAPL", weight=1.0)
        svc.upsert_holding(p2["portfolio_id"], user_id="u1", symbol="MSFT", weight=1.0)

        reloaded = PortfolioService(store=DatabasePortfolioStore(db))
        rows = reloaded.list_portfolios(user_id="u1")
        assert len(rows) == 2
        h1 = reloaded.list_holdings(p1["portfolio_id"], user_id="u1")
        h2 = reloaded.list_holdings(p2["portfolio_id"], user_id="u1")
        assert [h["symbol"] for h in h1] == ["AAPL"]
        assert [h["symbol"] for h in h2] == ["MSFT"]

    def test_delete_removes_snapshot_row_after_flush(self) -> None:
        db = InMemoryDatabasePort()
        svc = PortfolioService(store=DatabasePortfolioStore(db))
        portfolio = svc.create_portfolio(user_id="u1", name="Temp")
        pid = portfolio["portfolio_id"]
        svc.delete_portfolio(pid, user_id="u1")

        reloaded = PortfolioService(store=DatabasePortfolioStore(db))
        assert reloaded.list_portfolios(user_id="u1") == []
