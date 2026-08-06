"""Tests for portfolio_store.models."""

from __future__ import annotations

from portfolio_store.models import (
    TRANSACTION_TYPES,
    Holding,
    Portfolio,
    Transaction,
    WatchlistItem,
)


class TestPortfolio:
    def test_to_dict_shape(self) -> None:
        portfolio = Portfolio(
            portfolio_id="pf_1",
            user_id="u1",
            name="My Portfolio",
            is_default=True,
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
        )
        data = portfolio.to_dict()
        assert data["portfolio_id"] == "pf_1"
        assert data["org_id"] is None
        assert data["is_default"] is True
        assert data["metadata"] == {}

    def test_org_id_reserved_field(self) -> None:
        portfolio = Portfolio(
            portfolio_id="pf_1",
            user_id="u1",
            name="My Portfolio",
            is_default=False,
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
            org_id="org_1",
        )
        assert portfolio.to_dict()["org_id"] == "org_1"


class TestHolding:
    def test_to_dict_matches_position_input_shape(self) -> None:
        holding = Holding(
            holding_id="hld_1",
            portfolio_id="pf_1",
            symbol="AAPL",
            weight=0.5,
            created_at="2024-01-01T00:00:00+00:00",
            updated_at="2024-01-01T00:00:00+00:00",
            units=10.0,
            cost_basis_per_unit=150.0,
            purchase_date="2023-01-01",
            sector="Technology",
        )
        data = holding.to_dict()
        for key in (
            "symbol",
            "weight",
            "units",
            "cost_basis_per_unit",
            "purchase_date",
            "sector",
            "country",
            "exchange",
            "value_score",
            "quality_score",
            "momentum_score",
            "size_score",
            "volatility_score",
        ):
            assert key in data


class TestTransaction:
    def test_all_required_types_supported(self) -> None:
        expected = {
            "buy",
            "sell",
            "dividend",
            "bonus",
            "split",
            "rights",
            "fee",
            "tax",
            "cash_deposit",
            "cash_withdrawal",
        }
        assert set(TRANSACTION_TYPES) == expected

    def test_to_dict_shape(self) -> None:
        txn = Transaction(
            transaction_id="txn_1",
            portfolio_id="pf_1",
            transaction_type="buy",
            transaction_date="2024-01-01",
            created_at="2024-01-01T00:00:00+00:00",
            symbol="AAPL",
            quantity=10,
            price=150.0,
        )
        data = txn.to_dict()
        assert data["transaction_type"] == "buy"
        assert data["currency"] == "USD"


class TestWatchlistItem:
    def test_to_dict_shape(self) -> None:
        item = WatchlistItem(
            item_id="wl_1",
            portfolio_id="pf_1",
            symbol="MSFT",
            added_at="2024-01-01T00:00:00+00:00",
        )
        data = item.to_dict()
        assert data["symbol"] == "MSFT"
        assert data["label"] is None
