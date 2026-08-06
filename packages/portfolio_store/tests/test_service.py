"""Tests for portfolio_store.service.PortfolioService."""

from __future__ import annotations

import pytest

from portfolio_store.exceptions import ForbiddenError, NotFoundError, ValidationError
from portfolio_store.models import TRANSACTION_TYPES
from portfolio_store.service import PortfolioService


@pytest.fixture
def svc() -> PortfolioService:
    return PortfolioService()


class TestCreatePortfolio:
    def test_first_portfolio_is_always_default(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        assert portfolio["is_default"] is True

    def test_second_portfolio_not_default_unless_requested(
        self, svc: PortfolioService
    ) -> None:
        svc.create_portfolio(user_id="u1", name="First")
        second = svc.create_portfolio(user_id="u1", name="Second")
        assert second["is_default"] is False

    def test_requesting_default_demotes_previous_default(
        self, svc: PortfolioService
    ) -> None:
        first = svc.create_portfolio(user_id="u1", name="First")
        second = svc.create_portfolio(user_id="u1", name="Second", is_default=True)
        assert second["is_default"] is True
        refreshed_first = svc.get_portfolio(first["portfolio_id"], user_id="u1")
        assert refreshed_first["is_default"] is False

    def test_rejects_empty_name(self, svc: PortfolioService) -> None:
        with pytest.raises(ValidationError):
            svc.create_portfolio(user_id="u1", name="   ")

    def test_rejects_empty_user_id(self, svc: PortfolioService) -> None:
        with pytest.raises(ValidationError):
            svc.create_portfolio(user_id="  ", name="First")

    def test_benchmark_symbol_normalized(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(
            user_id="u1", name="First", benchmark_symbol=" spy "
        )
        assert portfolio["benchmark_symbol"] == "SPY"


class TestMultiPortfolio:
    def test_user_can_have_multiple_portfolios(self, svc: PortfolioService) -> None:
        svc.create_portfolio(user_id="u1", name="First")
        svc.create_portfolio(user_id="u1", name="Second")
        svc.create_portfolio(user_id="u1", name="Third")
        rows = svc.list_portfolios(user_id="u1")
        assert len(rows) == 3

    def test_default_portfolio_listed_first(self, svc: PortfolioService) -> None:
        svc.create_portfolio(user_id="u1", name="First")
        svc.create_portfolio(user_id="u1", name="Second", is_default=True)
        rows = svc.list_portfolios(user_id="u1")
        assert rows[0]["name"] == "Second"
        assert rows[0]["is_default"] is True

    def test_portfolios_isolated_per_user(self, svc: PortfolioService) -> None:
        svc.create_portfolio(user_id="u1", name="U1 Portfolio")
        svc.create_portfolio(user_id="u2", name="U2 Portfolio")
        assert len(svc.list_portfolios(user_id="u1")) == 1
        assert len(svc.list_portfolios(user_id="u2")) == 1

    def test_get_default_portfolio(self, svc: PortfolioService) -> None:
        svc.create_portfolio(user_id="u1", name="First")
        default = svc.get_default_portfolio(user_id="u1")
        assert default is not None
        assert default["name"] == "First"

    def test_get_default_portfolio_none_when_user_has_none(
        self, svc: PortfolioService
    ) -> None:
        assert svc.get_default_portfolio(user_id="ghost") is None


class TestOwnership:
    def test_get_portfolio_not_found(self, svc: PortfolioService) -> None:
        with pytest.raises(NotFoundError):
            svc.get_portfolio("missing", user_id="u1")

    def test_get_portfolio_forbidden_for_other_user(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ForbiddenError):
            svc.get_portfolio(portfolio["portfolio_id"], user_id="u2")

    def test_update_forbidden_for_other_user(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ForbiddenError):
            svc.update_portfolio(portfolio["portfolio_id"], user_id="u2", name="Hacked")

    def test_delete_forbidden_for_other_user(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ForbiddenError):
            svc.delete_portfolio(portfolio["portfolio_id"], user_id="u2")

    def test_holdings_forbidden_for_other_user(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ForbiddenError):
            svc.list_holdings(portfolio["portfolio_id"], user_id="u2")
        with pytest.raises(ForbiddenError):
            svc.upsert_holding(
                portfolio["portfolio_id"], user_id="u2", symbol="AAPL", weight=0.5
            )

    def test_watchlist_forbidden_for_other_user(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ForbiddenError):
            svc.add_watchlist_symbol(
                portfolio["portfolio_id"], user_id="u2", symbol="AAPL"
            )

    def test_transactions_forbidden_for_other_user(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ForbiddenError):
            svc.record_transaction(
                portfolio["portfolio_id"],
                user_id="u2",
                transaction_type="buy",
                transaction_date="2024-01-01",
            )


class TestUpdateAndDeletePortfolio:
    def test_update_name(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        updated = svc.update_portfolio(
            portfolio["portfolio_id"], user_id="u1", name="Renamed"
        )
        assert updated["name"] == "Renamed"

    def test_set_benchmark(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        updated = svc.set_benchmark(
            portfolio["portfolio_id"], user_id="u1", benchmark_symbol="qqq"
        )
        assert updated["benchmark_symbol"] == "QQQ"

    def test_clear_benchmark(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(
            user_id="u1", name="First", benchmark_symbol="SPY"
        )
        updated = svc.set_benchmark(
            portfolio["portfolio_id"], user_id="u1", benchmark_symbol=None
        )
        assert updated["benchmark_symbol"] is None

    def test_delete_portfolio_cascades_holdings_and_watchlist(
        self, svc: PortfolioService
    ) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        svc.upsert_holding(pid, user_id="u1", symbol="AAPL", weight=1.0)
        svc.add_watchlist_symbol(pid, user_id="u1", symbol="MSFT")
        assert svc.delete_portfolio(pid, user_id="u1") is True
        with pytest.raises(NotFoundError):
            svc.get_portfolio(pid, user_id="u1")

    def test_deleting_default_promotes_another_portfolio(
        self, svc: PortfolioService
    ) -> None:
        first = svc.create_portfolio(user_id="u1", name="First")
        second = svc.create_portfolio(user_id="u1", name="Second")
        svc.delete_portfolio(first["portfolio_id"], user_id="u1")
        refreshed_second = svc.get_portfolio(second["portfolio_id"], user_id="u1")
        assert refreshed_second["is_default"] is True


class TestHoldings:
    def test_upsert_creates_holding(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        holding = svc.upsert_holding(
            portfolio["portfolio_id"],
            user_id="u1",
            symbol="aapl",
            weight=0.6,
            sector="Technology",
        )
        assert holding["symbol"] == "AAPL"
        assert holding["weight"] == 0.6

    def test_upsert_updates_existing_holding_by_symbol(
        self, svc: PortfolioService
    ) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        first = svc.upsert_holding(pid, user_id="u1", symbol="AAPL", weight=0.5)
        second = svc.upsert_holding(pid, user_id="u1", symbol="AAPL", weight=0.8)
        assert second["holding_id"] == first["holding_id"]
        assert second["weight"] == 0.8
        assert len(svc.list_holdings(pid, user_id="u1")) == 1

    def test_rejects_negative_weight(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ValidationError):
            svc.upsert_holding(
                portfolio["portfolio_id"], user_id="u1", symbol="AAPL", weight=-0.1
            )

    def test_remove_holding(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        svc.upsert_holding(pid, user_id="u1", symbol="AAPL", weight=0.5)
        assert svc.remove_holding(pid, user_id="u1", symbol="aapl") is True
        assert svc.list_holdings(pid, user_id="u1") == []

    def test_remove_missing_holding_returns_false(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        assert (
            svc.remove_holding(portfolio["portfolio_id"], user_id="u1", symbol="AAPL")
            is False
        )

    def test_holdings_linked_to_correct_portfolio(self, svc: PortfolioService) -> None:
        p1 = svc.create_portfolio(user_id="u1", name="First")
        p2 = svc.create_portfolio(user_id="u1", name="Second")
        svc.upsert_holding(p1["portfolio_id"], user_id="u1", symbol="AAPL", weight=1.0)
        svc.upsert_holding(p2["portfolio_id"], user_id="u1", symbol="MSFT", weight=1.0)
        assert [h["symbol"] for h in svc.list_holdings(p1["portfolio_id"], user_id="u1")] == [
            "AAPL"
        ]
        assert [h["symbol"] for h in svc.list_holdings(p2["portfolio_id"], user_id="u1")] == [
            "MSFT"
        ]


class TestTransactions:
    @pytest.mark.parametrize("transaction_type", TRANSACTION_TYPES)
    def test_every_supported_transaction_type_recorded(
        self, svc: PortfolioService, transaction_type: str
    ) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        txn = svc.record_transaction(
            portfolio["portfolio_id"],
            user_id="u1",
            transaction_type=transaction_type,
            transaction_date="2024-01-01",
            symbol="AAPL" if transaction_type not in {"cash_deposit", "cash_withdrawal"} else None,
            amount=100.0,
        )
        assert txn["transaction_type"] == transaction_type

    def test_rejects_unknown_transaction_type(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        with pytest.raises(ValidationError):
            svc.record_transaction(
                portfolio["portfolio_id"],
                user_id="u1",
                transaction_type="short_sell",
                transaction_date="2024-01-01",
            )

    def test_list_transactions_newest_first(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        svc.record_transaction(
            pid, user_id="u1", transaction_type="buy",
            transaction_date="2024-01-01", symbol="AAPL", quantity=1, price=100,
        )
        svc.record_transaction(
            pid, user_id="u1", transaction_type="buy",
            transaction_date="2024-06-01", symbol="AAPL", quantity=1, price=120,
        )
        rows = svc.list_transactions(pid, user_id="u1")
        assert rows[0]["transaction_date"] == "2024-06-01"

    def test_list_transactions_filter_by_symbol(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        svc.record_transaction(
            pid, user_id="u1", transaction_type="buy",
            transaction_date="2024-01-01", symbol="AAPL", quantity=1, price=100,
        )
        svc.record_transaction(
            pid, user_id="u1", transaction_type="buy",
            transaction_date="2024-01-02", symbol="MSFT", quantity=1, price=100,
        )
        rows = svc.list_transactions(pid, user_id="u1", symbol="msft")
        assert len(rows) == 1
        assert rows[0]["symbol"] == "MSFT"

    def test_cash_transactions_do_not_require_symbol(
        self, svc: PortfolioService
    ) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        txn = svc.record_transaction(
            portfolio["portfolio_id"],
            user_id="u1",
            transaction_type="cash_deposit",
            transaction_date="2024-01-01",
            amount=1000.0,
        )
        assert txn["symbol"] is None
        assert txn["amount"] == 1000.0

    def test_transactions_isolated_per_portfolio(self, svc: PortfolioService) -> None:
        p1 = svc.create_portfolio(user_id="u1", name="First")
        p2 = svc.create_portfolio(user_id="u1", name="Second")
        svc.record_transaction(
            p1["portfolio_id"], user_id="u1", transaction_type="buy",
            transaction_date="2024-01-01", symbol="AAPL", quantity=1, price=100,
        )
        assert len(svc.list_transactions(p1["portfolio_id"], user_id="u1")) == 1
        assert len(svc.list_transactions(p2["portfolio_id"], user_id="u1")) == 0


class TestWatchlist:
    def test_add_and_list_watchlist_symbol(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        svc.add_watchlist_symbol(pid, user_id="u1", symbol="nvda", label="AI chips")
        rows = svc.list_watchlist(pid, user_id="u1")
        assert rows[0]["symbol"] == "NVDA"
        assert rows[0]["label"] == "AI chips"

    def test_add_watchlist_symbol_idempotent(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        svc.add_watchlist_symbol(pid, user_id="u1", symbol="NVDA")
        svc.add_watchlist_symbol(pid, user_id="u1", symbol="nvda")
        assert len(svc.list_watchlist(pid, user_id="u1")) == 1

    def test_remove_watchlist_symbol(self, svc: PortfolioService) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        pid = portfolio["portfolio_id"]
        svc.add_watchlist_symbol(pid, user_id="u1", symbol="NVDA")
        assert svc.remove_watchlist_symbol(pid, user_id="u1", symbol="nvda") is True
        assert svc.list_watchlist(pid, user_id="u1") == []

    def test_remove_missing_watchlist_symbol_returns_false(
        self, svc: PortfolioService
    ) -> None:
        portfolio = svc.create_portfolio(user_id="u1", name="First")
        assert (
            svc.remove_watchlist_symbol(portfolio["portfolio_id"], user_id="u1", symbol="AAPL")
            is False
        )


class TestMigration:
    def test_migrates_local_holdings_and_watchlist(self, svc: PortfolioService) -> None:
        result = svc.migrate_local_portfolio(
            user_id="u1",
            name="My Portfolio",
            holdings=[
                {"symbol": "AAPL", "allocationPercent": 60, "sector": "Technology"},
                {"symbol": "MSFT", "weight": 0.4},
            ],
            watchlist=[{"symbol": "NVDA", "label": "AI"}],
            benchmark_symbol="SPY",
        )
        assert result["migrated"] is True
        pid = result["portfolio"]["portfolio_id"]
        holdings = svc.list_holdings(pid, user_id="u1")
        assert {h["symbol"] for h in holdings} == {"AAPL", "MSFT"}
        aapl = next(h for h in holdings if h["symbol"] == "AAPL")
        assert aapl["weight"] == pytest.approx(0.6)
        assert svc.list_watchlist(pid, user_id="u1")[0]["symbol"] == "NVDA"
        assert result["portfolio"]["benchmark_symbol"] == "SPY"

    def test_migration_is_idempotent_never_overwrites_existing_server_portfolio(
        self, svc: PortfolioService
    ) -> None:
        first = svc.migrate_local_portfolio(
            user_id="u1",
            name="Original",
            holdings=[{"symbol": "AAPL", "weight": 1.0}],
        )
        assert first["migrated"] is True

        second = svc.migrate_local_portfolio(
            user_id="u1",
            name="Different Local Copy",
            holdings=[{"symbol": "TSLA", "weight": 1.0}],
        )
        assert second["migrated"] is False
        assert second["portfolio"]["portfolio_id"] == first["portfolio"]["portfolio_id"]
        # Server data from the first migration is untouched by the retry.
        holdings = svc.list_holdings(second["portfolio"]["portfolio_id"], user_id="u1")
        assert [h["symbol"] for h in holdings] == ["AAPL"]

    def test_migrates_empty_local_portfolio(self, svc: PortfolioService) -> None:
        result = svc.migrate_local_portfolio(user_id="u1", name="Empty")
        assert result["migrated"] is True
        assert svc.list_holdings(result["portfolio"]["portfolio_id"], user_id="u1") == []


class TestSchema:
    def test_schema_lists_transaction_types_and_rules(
        self, svc: PortfolioService
    ) -> None:
        schema = svc.schema()
        assert set(schema["transaction_types"]) == set(TRANSACTION_TYPES)
        assert "every_portfolio_owned_by_authenticated_user" in schema["rules"]
        assert "organization_ownership_reserved_not_implemented" in schema["rules"]
