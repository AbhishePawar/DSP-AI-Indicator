"""Tests for dsp_platform.portfolio_store_facade and DSPPlatform delegation."""

from __future__ import annotations

import pytest

from dsp_platform import PlatformBuilder, PlatformConfiguration
from dsp_platform.portfolio_store_facade import reset_portfolio_store_for_tests
from portfolio_store import PortfolioService


@pytest.fixture(autouse=True)
def _fresh_store():
    reset_portfolio_store_for_tests(PortfolioService())
    yield
    reset_portfolio_store_for_tests(None)


@pytest.fixture
def platform():
    return (
        PlatformBuilder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


class TestFacadeFunctions:
    def test_schema_exposes_transaction_types(self) -> None:
        from dsp_platform.portfolio_store_facade import portfolio_store_schema

        schema = portfolio_store_schema()
        assert "buy" in schema["transaction_types"]
        assert "cash_withdrawal" in schema["transaction_types"]

    def test_create_and_get_portfolio(self) -> None:
        from dsp_platform.portfolio_store_facade import create_portfolio, get_portfolio

        created = create_portfolio(user_id="u1", name="My Portfolio")
        fetched = get_portfolio(created["portfolio_id"], user_id="u1")
        assert fetched["name"] == "My Portfolio"
        assert fetched["is_default"] is True


class TestDSPPlatformDelegation:
    def test_create_list_get_update_delete_portfolio(self, platform) -> None:
        created = platform.create_portfolio(user_id="u1", name="First")
        pid = created["portfolio_id"]

        rows = platform.list_portfolios(user_id="u1")
        assert len(rows) == 1

        fetched = platform.get_portfolio(pid, user_id="u1")
        assert fetched["portfolio_id"] == pid

        updated = platform.update_portfolio(pid, user_id="u1", name="Renamed")
        assert updated["name"] == "Renamed"

        default = platform.get_default_portfolio(user_id="u1")
        assert default is not None
        assert default["portfolio_id"] == pid

        assert platform.delete_portfolio(pid, user_id="u1") is True
        assert platform.list_portfolios(user_id="u1") == []

    def test_benchmark_lifecycle(self, platform) -> None:
        created = platform.create_portfolio(user_id="u1", name="First")
        pid = created["portfolio_id"]
        updated = platform.set_portfolio_benchmark(
            pid, user_id="u1", benchmark_symbol="spy"
        )
        assert updated["benchmark_symbol"] == "SPY"
        cleared = platform.set_portfolio_benchmark(
            pid, user_id="u1", benchmark_symbol=None
        )
        assert cleared["benchmark_symbol"] is None

    def test_holdings_crud(self, platform) -> None:
        created = platform.create_portfolio(user_id="u1", name="First")
        pid = created["portfolio_id"]
        holding = platform.upsert_portfolio_holding(
            pid, user_id="u1", symbol="AAPL", weight=0.5, sector="Technology"
        )
        assert holding["symbol"] == "AAPL"
        rows = platform.list_portfolio_holdings(pid, user_id="u1")
        assert len(rows) == 1
        assert platform.remove_portfolio_holding(pid, user_id="u1", symbol="AAPL") is True
        assert platform.list_portfolio_holdings(pid, user_id="u1") == []

    def test_transactions_crud(self, platform) -> None:
        created = platform.create_portfolio(user_id="u1", name="First")
        pid = created["portfolio_id"]
        txn = platform.record_portfolio_transaction(
            pid,
            user_id="u1",
            transaction_type="buy",
            transaction_date="2024-01-01",
            symbol="AAPL",
            quantity=10,
            price=150,
        )
        assert txn["transaction_type"] == "buy"
        rows = platform.list_portfolio_transactions(pid, user_id="u1")
        assert len(rows) == 1

    def test_watchlist_crud(self, platform) -> None:
        created = platform.create_portfolio(user_id="u1", name="First")
        pid = created["portfolio_id"]
        platform.add_portfolio_watchlist_symbol(pid, user_id="u1", symbol="NVDA")
        rows = platform.list_portfolio_watchlist(pid, user_id="u1")
        assert rows[0]["symbol"] == "NVDA"
        assert platform.remove_portfolio_watchlist_symbol(
            pid, user_id="u1", symbol="NVDA"
        ) is True

    def test_migrate_local_portfolio(self, platform) -> None:
        result = platform.migrate_local_portfolio(
            user_id="u1",
            name="Migrated",
            holdings=[{"symbol": "AAPL", "allocationPercent": 100}],
        )
        assert result["migrated"] is True
        pid = result["portfolio"]["portfolio_id"]
        holdings = platform.list_portfolio_holdings(pid, user_id="u1")
        assert holdings[0]["symbol"] == "AAPL"

    def test_ownership_enforced_across_users(self, platform) -> None:
        from portfolio_store import ForbiddenError

        created = platform.create_portfolio(user_id="u1", name="First")
        pid = created["portfolio_id"]
        with pytest.raises(ForbiddenError):
            platform.get_portfolio(pid, user_id="u2")
