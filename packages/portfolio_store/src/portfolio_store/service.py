"""Portfolio persistence service (RC1 Milestone 3).

Ownership-checked CRUD over ``PortfolioStorePort``. No analytics, no
valuation, no scoring — see README. Mirrors ``enterprise.EnterpriseService``'s
structure (store abstraction + singleton factory + explicit ``flush()``
after each mutation).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any

from portfolio_store.exceptions import ForbiddenError, NotFoundError, ValidationError
from portfolio_store.models import (
    PORTFOLIO_STORE_SCHEMA_VERSION,
    PORTFOLIO_STORE_SERVICE_VERSION,
    TRANSACTION_TYPES,
    Holding,
    Portfolio,
    Transaction,
    WatchlistItem,
    freeze_mapping,
    utc_now,
)
from portfolio_store.ports import PortfolioStorePort
from portfolio_store.store import InMemoryPortfolioStore

__all__ = [
    "PortfolioService",
    "get_portfolio_service",
    "reset_portfolio_service_for_tests",
]

_UNSET: Any = object()


class PortfolioService:
    """Server-side ownership store for Portfolio/Holdings/Transactions/Watchlist."""

    def __init__(
        self, store: PortfolioStorePort | InMemoryPortfolioStore | None = None
    ) -> None:
        self.store: PortfolioStorePort = store or InMemoryPortfolioStore()

    # ------------------------------------------------------------------ schema
    def schema(self) -> dict[str, Any]:
        return {
            "schema_version": PORTFOLIO_STORE_SCHEMA_VERSION,
            "service_version": PORTFOLIO_STORE_SERVICE_VERSION,
            "transaction_types": list(TRANSACTION_TYPES),
            "capabilities": [
                "portfolio_crud",
                "multi_portfolio_per_user",
                "default_portfolio",
                "holdings_linked_to_portfolio",
                "transaction_ledger_append_only",
                "watchlist_per_portfolio",
                "benchmark_selection",
                "local_to_server_migration",
                "durable_store_when_database_port_supplied",
            ],
            "rules": [
                "every_portfolio_owned_by_authenticated_user",
                "organization_ownership_reserved_not_implemented",
                "no_analytics_no_valuation_in_this_package",
                "no_holding_reconciliation_from_transactions",
                "never_delete_local_data_from_server_migration",
            ],
        }

    # --------------------------------------------------------------- ownership
    def _get_owned_portfolio(self, portfolio_id: str, *, user_id: str) -> Portfolio:
        portfolio = self.store.portfolios.get(portfolio_id)
        if portfolio is None:
            raise NotFoundError(f"portfolio not found: {portfolio_id}")
        if portfolio.user_id != user_id:
            raise ForbiddenError("not the owner of this portfolio")
        return portfolio

    # -------------------------------------------------------------- portfolios
    def create_portfolio(
        self,
        *,
        user_id: str,
        name: str,
        is_default: bool | None = None,
        benchmark_symbol: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        portfolio_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        uid = str(user_id or "").strip()
        clean_name = str(name or "").strip()
        if not uid:
            raise ValidationError("user_id required")
        if not clean_name:
            raise ValidationError("name required")
        pid = (portfolio_id or f"pf_{uuid.uuid4().hex[:16]}").strip()
        if pid in self.store.portfolios:
            raise ValidationError("portfolio_id already exists")
        now = created_at or utc_now().isoformat()
        existing = [p for p in self.store.portfolios.values() if p.user_id == uid]
        # The user's first portfolio is always the default; otherwise honor the
        # caller's request (defaulting to False for additional portfolios).
        make_default = bool(is_default) or not existing
        if make_default:
            self._clear_default(uid)
        portfolio = Portfolio(
            portfolio_id=pid,
            user_id=uid,
            name=clean_name,
            is_default=make_default,
            created_at=now,
            updated_at=now,
            benchmark_symbol=(
                benchmark_symbol.strip().upper() if benchmark_symbol else None
            ),
            metadata=freeze_mapping(metadata),
        )
        self.store.portfolios[pid] = portfolio
        self.store.flush()
        return portfolio.to_dict()

    def _clear_default(self, user_id: str) -> None:
        for pid, portfolio in list(self.store.portfolios.items()):
            if portfolio.user_id == user_id and portfolio.is_default:
                self.store.portfolios[pid] = _replace_portfolio(
                    portfolio, is_default=False
                )

    def list_portfolios(self, *, user_id: str) -> list[dict[str, Any]]:
        rows = [p for p in self.store.portfolios.values() if p.user_id == user_id]
        rows.sort(key=lambda p: (not p.is_default, p.created_at))
        return [p.to_dict() for p in rows]

    def get_portfolio(self, portfolio_id: str, *, user_id: str) -> dict[str, Any]:
        return self._get_owned_portfolio(portfolio_id, user_id=user_id).to_dict()

    def get_default_portfolio(self, *, user_id: str) -> dict[str, Any] | None:
        for portfolio in self.store.portfolios.values():
            if portfolio.user_id == user_id and portfolio.is_default:
                return portfolio.to_dict()
        return None

    def update_portfolio(
        self,
        portfolio_id: str,
        *,
        user_id: str,
        name: str | None = None,
        is_default: bool | None = None,
        benchmark_symbol: str | None = _UNSET,
        metadata: Mapping[str, Any] | None = None,
        updated_at: str | None = None,
    ) -> dict[str, Any]:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id=user_id)
        if is_default:
            self._clear_default(user_id)
            portfolio = self.store.portfolios[portfolio_id]
        new_name = str(name).strip() if name is not None else portfolio.name
        if name is not None and not new_name:
            raise ValidationError("name must not be empty")
        new_benchmark = portfolio.benchmark_symbol
        if benchmark_symbol is not _UNSET:
            new_benchmark = (
                benchmark_symbol.strip().upper() if benchmark_symbol else None
            )
        new_is_default = (
            bool(is_default) if is_default is not None else portfolio.is_default
        )
        new_metadata = (
            freeze_mapping(metadata) if metadata is not None else portfolio.metadata
        )
        updated = _replace_portfolio(
            portfolio,
            name=new_name,
            is_default=new_is_default,
            benchmark_symbol=new_benchmark,
            metadata=new_metadata,
            updated_at=updated_at or utc_now().isoformat(),
        )
        self.store.portfolios[portfolio_id] = updated
        self.store.flush()
        return updated.to_dict()

    def set_benchmark(
        self, portfolio_id: str, *, user_id: str, benchmark_symbol: str | None
    ) -> dict[str, Any]:
        return self.update_portfolio(
            portfolio_id, user_id=user_id, benchmark_symbol=benchmark_symbol
        )

    def delete_portfolio(self, portfolio_id: str, *, user_id: str) -> bool:
        portfolio = self._get_owned_portfolio(portfolio_id, user_id=user_id)
        del self.store.portfolios[portfolio_id]
        for hid in [
            h for h, holding in self.store.holdings.items()
            if holding.portfolio_id == portfolio_id
        ]:
            del self.store.holdings[hid]
        for wid in [
            w for w, item in self.store.watchlist_items.items()
            if item.portfolio_id == portfolio_id
        ]:
            del self.store.watchlist_items[wid]
        # If the deleted portfolio was the default, promote the oldest
        # remaining portfolio (if any) so `is_default` stays a real invariant.
        if portfolio.is_default:
            remaining = sorted(
                (p for p in self.store.portfolios.values() if p.user_id == user_id),
                key=lambda p: p.created_at,
            )
            if remaining:
                promoted = remaining[0]
                self.store.portfolios[promoted.portfolio_id] = _replace_portfolio(
                    promoted, is_default=True
                )
        self.store.flush()
        return True

    # ---------------------------------------------------------------- holdings
    def list_holdings(self, portfolio_id: str, *, user_id: str) -> list[dict[str, Any]]:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        rows = [
            h for h in self.store.holdings.values() if h.portfolio_id == portfolio_id
        ]
        rows.sort(key=lambda h: h.symbol)
        return [h.to_dict() for h in rows]

    def upsert_holding(
        self,
        portfolio_id: str,
        *,
        user_id: str,
        symbol: str,
        weight: float,
        units: float | None = None,
        cost_basis_per_unit: float | None = None,
        purchase_date: str | None = None,
        sector: str | None = None,
        country: str | None = None,
        exchange: str | None = None,
        value_score: float | None = None,
        quality_score: float | None = None,
        momentum_score: float | None = None,
        size_score: float | None = None,
        volatility_score: float | None = None,
        holding_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol:
            raise ValidationError("symbol required")
        try:
            clean_weight = float(weight)
        except (TypeError, ValueError) as exc:
            raise ValidationError("weight must be a number") from exc
        if clean_weight < 0:
            raise ValidationError("weight must be >= 0")

        existing = next(
            (
                h
                for h in self.store.holdings.values()
                if h.portfolio_id == portfolio_id and h.symbol == clean_symbol
            ),
            None,
        )
        now = utc_now().isoformat()
        new_hid = holding_id or f"hld_{uuid.uuid4().hex[:16]}"
        hid = existing.holding_id if existing else new_hid
        holding = Holding(
            holding_id=hid,
            portfolio_id=portfolio_id,
            symbol=clean_symbol,
            weight=clean_weight,
            created_at=existing.created_at if existing else (created_at or now),
            updated_at=now,
            units=units,
            cost_basis_per_unit=cost_basis_per_unit,
            purchase_date=purchase_date,
            sector=sector,
            country=country,
            exchange=exchange,
            value_score=value_score,
            quality_score=quality_score,
            momentum_score=momentum_score,
            size_score=size_score,
            volatility_score=volatility_score,
        )
        self.store.holdings[hid] = holding
        self.store.flush()
        return holding.to_dict()

    def remove_holding(self, portfolio_id: str, *, user_id: str, symbol: str) -> bool:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        clean_symbol = str(symbol or "").strip().upper()
        target = next(
            (
                hid
                for hid, h in self.store.holdings.items()
                if h.portfolio_id == portfolio_id and h.symbol == clean_symbol
            ),
            None,
        )
        if target is None:
            return False
        del self.store.holdings[target]
        self.store.flush()
        return True

    # ------------------------------------------------------------- transactions
    def record_transaction(
        self,
        portfolio_id: str,
        *,
        user_id: str,
        transaction_type: str,
        transaction_date: str,
        symbol: str | None = None,
        quantity: float | None = None,
        price: float | None = None,
        amount: float | None = None,
        currency: str = "USD",
        notes: str | None = None,
        transaction_id: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        clean_type = str(transaction_type or "").strip().lower()
        if clean_type not in TRANSACTION_TYPES:
            raise ValidationError(
                f"invalid transaction_type {transaction_type!r}; "
                f"expected one of {TRANSACTION_TYPES}"
            )
        clean_date = str(transaction_date or "").strip()
        if not clean_date:
            raise ValidationError("transaction_date required")
        tid = transaction_id or f"txn_{uuid.uuid4().hex[:16]}"
        transaction = Transaction(
            transaction_id=tid,
            portfolio_id=portfolio_id,
            transaction_type=clean_type,
            transaction_date=clean_date,
            created_at=created_at or utc_now().isoformat(),
            symbol=(symbol.strip().upper() if symbol else None),
            quantity=quantity,
            price=price,
            amount=amount,
            currency=(currency or "USD").strip().upper(),
            notes=notes,
        )
        self.store.transactions.append(transaction)
        self.store.flush()
        return transaction.to_dict()

    def list_transactions(
        self,
        portfolio_id: str,
        *,
        user_id: str,
        symbol: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        rows = [t for t in self.store.transactions if t.portfolio_id == portfolio_id]
        if symbol:
            clean = symbol.strip().upper()
            rows = [t for t in rows if t.symbol == clean]
        rows.sort(key=lambda t: (t.transaction_date, t.created_at), reverse=True)
        return [t.to_dict() for t in rows[: max(1, int(limit))]]

    # --------------------------------------------------------------- watchlist
    def list_watchlist(
        self, portfolio_id: str, *, user_id: str
    ) -> list[dict[str, Any]]:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        rows = [
            w for w in self.store.watchlist_items.values()
            if w.portfolio_id == portfolio_id
        ]
        rows.sort(key=lambda w: w.added_at, reverse=True)
        return [w.to_dict() for w in rows]

    def add_watchlist_symbol(
        self,
        portfolio_id: str,
        *,
        user_id: str,
        symbol: str,
        label: str | None = None,
        item_id: str | None = None,
        added_at: str | None = None,
    ) -> dict[str, Any]:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol:
            raise ValidationError("symbol required")
        existing = next(
            (
                w
                for w in self.store.watchlist_items.values()
                if w.portfolio_id == portfolio_id and w.symbol == clean_symbol
            ),
            None,
        )
        if existing is not None:
            return existing.to_dict()
        wid = item_id or f"wl_{uuid.uuid4().hex[:16]}"
        item = WatchlistItem(
            item_id=wid,
            portfolio_id=portfolio_id,
            symbol=clean_symbol,
            added_at=added_at or utc_now().isoformat(),
            label=label,
        )
        self.store.watchlist_items[wid] = item
        self.store.flush()
        return item.to_dict()

    def remove_watchlist_symbol(
        self, portfolio_id: str, *, user_id: str, symbol: str
    ) -> bool:
        self._get_owned_portfolio(portfolio_id, user_id=user_id)
        clean_symbol = str(symbol or "").strip().upper()
        target = next(
            (
                wid
                for wid, w in self.store.watchlist_items.items()
                if w.portfolio_id == portfolio_id and w.symbol == clean_symbol
            ),
            None,
        )
        if target is None:
            return False
        del self.store.watchlist_items[target]
        self.store.flush()
        return True

    # --------------------------------------------------------------- migration
    def migrate_local_portfolio(
        self,
        *,
        user_id: str,
        name: str = "My Portfolio",
        holdings: list[Mapping[str, Any]] | None = None,
        watchlist: list[Mapping[str, Any]] | None = None,
        benchmark_symbol: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        """Create the user's default portfolio from local (browser) data.

        Idempotent and safe to call repeatedly: if the user already has a
        default portfolio on the server, this returns it unchanged
        (``migrated: False``) — the caller's local copy is never assumed
        stale and the server is never overwritten by a stray retry. Only
        when the user has **no** portfolio yet does this create one from
        the supplied local snapshot (``migrated: True``).
        """
        existing = self.get_default_portfolio(user_id=user_id)
        if existing is not None:
            return {"migrated": False, "portfolio": existing}

        portfolio = self.create_portfolio(
            user_id=user_id,
            name=name,
            is_default=True,
            benchmark_symbol=benchmark_symbol,
            created_at=created_at,
        )
        portfolio_id = portfolio["portfolio_id"]
        for row in holdings or ():
            symbol = row.get("symbol") or row.get("ticker")
            weight = row.get("weight")
            if weight is None and "allocationPercent" in row:
                pct = row.get("allocationPercent")
                weight = (float(pct) / 100.0) if isinstance(pct, (int, float)) else None
            if not symbol or weight is None:
                continue
            self.upsert_holding(
                portfolio_id,
                user_id=user_id,
                symbol=str(symbol),
                weight=float(weight),
                sector=row.get("sector"),
                country=row.get("country"),
                exchange=row.get("exchange"),
                units=row.get("units"),
                cost_basis_per_unit=row.get("cost_basis_per_unit"),
                purchase_date=row.get("purchase_date"),
            )
        for row in watchlist or ():
            symbol = row.get("symbol")
            if not symbol:
                continue
            self.add_watchlist_symbol(
                portfolio_id,
                user_id=user_id,
                symbol=str(symbol),
                label=row.get("label"),
                added_at=row.get("addedAt") or row.get("added_at"),
            )
        return {
            "migrated": True,
            "portfolio": self.get_portfolio(portfolio_id, user_id=user_id),
        }


def _replace_portfolio(portfolio: Portfolio, **changes: Any) -> Portfolio:
    data = portfolio.to_dict()
    data.update(changes)
    return Portfolio(
        portfolio_id=data["portfolio_id"],
        user_id=data["user_id"],
        name=data["name"],
        is_default=data["is_default"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        org_id=data.get("org_id"),
        benchmark_symbol=data.get("benchmark_symbol"),
        metadata=freeze_mapping(data.get("metadata")),
    )


_SVC: PortfolioService | None = None


def get_portfolio_service(*, database: Any | None = None) -> PortfolioService:
    """Return process singleton — durable store when a DatabasePort is supplied."""
    global _SVC
    if _SVC is None:
        store: PortfolioStorePort | None = None
        if database is not None:
            from portfolio_store.db_store import DatabasePortfolioStore

            store = DatabasePortfolioStore(database)
        _SVC = PortfolioService(store=store)
    return _SVC


def reset_portfolio_service_for_tests(service: PortfolioService | None = None) -> None:
    global _SVC
    _SVC = service
