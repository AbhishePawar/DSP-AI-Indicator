"""DatabasePort-backed portfolio store (RC1 Milestone 3).

Mirrors ``enterprise.db_store.DatabaseEnterpriseStore`` exactly: one JSON
snapshot row per mutable working-set unit (here, one row per portfolio —
its holdings + watchlist + own fields) plus a true append-only table for
the transaction ledger (mirrors the enterprise audit log). Uses
``InMemoryDatabasePort``'s limited SQL dialect and any real
``production_platform.DatabasePort`` implementation identically — no import
dependency on ``production_platform`` is added (duck-typed, same convention
as ``enterprise.db_store``).
"""

from __future__ import annotations

import base64
import json
from threading import Lock
from typing import Any

from portfolio_store.models import (
    Holding,
    Portfolio,
    Transaction,
    WatchlistItem,
    freeze_mapping,
    utc_now,
)
from portfolio_store.store import InMemoryPortfolioStore

__all__ = [
    "PORTFOLIO_STORE_MIGRATIONS_SQL",
    "DatabasePortfolioStore",
    "build_portfolio_store",
]

PORTFOLIO_STORE_MIGRATIONS_SQL = (
    """
    CREATE TABLE IF NOT EXISTS portfolio_snapshots (
        portfolio_id TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolio_transactions_log (
        transaction_id TEXT PRIMARY KEY,
        portfolio_id TEXT NOT NULL,
        transaction_type TEXT NOT NULL,
        transaction_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        symbol TEXT,
        quantity TEXT,
        price TEXT,
        amount TEXT,
        currency TEXT NOT NULL,
        notes TEXT
    )
    """,
)


class DatabasePortfolioStore(InMemoryPortfolioStore):
    """Portfolio store hydrated from / flushed to a ``DatabasePort``."""

    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self.ensure_schema()
        self.hydrate()

    def ensure_schema(self) -> None:
        for stmt in PORTFOLIO_STORE_MIGRATIONS_SQL:
            self._db.execute(stmt.strip())

    def hydrate(self) -> None:
        rows = self._db.fetchall("SELECT * FROM portfolio_snapshots")
        portfolios: dict[str, Portfolio] = {}
        holdings: dict[str, Holding] = {}
        watchlist_items: dict[str, WatchlistItem] = {}
        for row in rows:
            raw = row.get("payload")
            payload = raw if isinstance(raw, dict) else _decode_payload(str(raw or ""))
            if not payload:
                continue
            portfolio_data = payload.get("portfolio")
            if portfolio_data:
                portfolio = _portfolio_from_dict(portfolio_data)
                portfolios[portfolio.portfolio_id] = portfolio
            for hid, hdata in (payload.get("holdings") or {}).items():
                holdings[hid] = _holding_from_dict(hdata)
            for wid, wdata in (payload.get("watchlist_items") or {}).items():
                watchlist_items[wid] = _watchlist_item_from_dict(wdata)
        with self._lock:
            self.portfolios = portfolios
            self.holdings = holdings
            self.watchlist_items = watchlist_items
        self._hydrate_transactions_only()

    def _hydrate_transactions_only(self) -> None:
        rows = self._db.fetchall("SELECT * FROM portfolio_transactions_log")
        records = [
            _transaction_from_row(r)
            for r in sorted(rows, key=lambda r: str(r.get("created_at") or ""))
        ]
        with self._lock:
            self.transactions = records

    def flush(self) -> None:
        """Persist the full working set + append-only transaction rows."""
        with self._persist_lock:
            with self._lock:
                portfolios = dict(self.portfolios)
                holdings = dict(self.holdings)
                watchlist_items = dict(self.watchlist_items)

            by_portfolio_holdings: dict[str, dict[str, Any]] = {}
            for hid, holding in holdings.items():
                by_portfolio_holdings.setdefault(holding.portfolio_id, {})[hid] = (
                    holding.to_dict()
                )
            by_portfolio_watchlist: dict[str, dict[str, Any]] = {}
            for wid, item in watchlist_items.items():
                by_portfolio_watchlist.setdefault(item.portfolio_id, {})[wid] = (
                    item.to_dict()
                )

            # InMemoryDatabasePort DELETE clears the whole table — rewrite
            # every snapshot row on each flush (matches enterprise's approach).
            self._db.execute("DELETE FROM portfolio_snapshots")
            now = utc_now().isoformat()
            for portfolio_id, portfolio in portfolios.items():
                snapshot = {
                    "portfolio": portfolio.to_dict(),
                    "holdings": by_portfolio_holdings.get(portfolio_id, {}),
                    "watchlist_items": by_portfolio_watchlist.get(portfolio_id, {}),
                }
                encoded = base64.b64encode(
                    json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
                ).decode("ascii")
                self._db.execute(
                    "INSERT INTO portfolio_snapshots "
                    "(portfolio_id, payload, updated_at) VALUES "
                    f"({_sql_literal(portfolio_id)}, {_sql_literal(encoded)}, "
                    f"{_sql_literal(now)})"
                )
            self._flush_transactions_append_only()

    def _flush_transactions_append_only(self) -> None:
        """Insert missing transaction rows — never update/delete existing ones."""
        existing_ids = {
            str(r.get("transaction_id"))
            for r in self._db.fetchall("SELECT * FROM portfolio_transactions_log")
        }
        with self._lock:
            pending = list(self.transactions)
        for record in pending:
            if record.transaction_id in existing_ids:
                continue
            cols = (
                "transaction_id, portfolio_id, transaction_type, transaction_date, "
                "created_at, symbol, quantity, price, amount, currency, notes"
            )
            vals = ", ".join(
                [
                    _sql_literal(record.transaction_id),
                    _sql_literal(record.portfolio_id),
                    _sql_literal(record.transaction_type),
                    _sql_literal(record.transaction_date),
                    _sql_literal(record.created_at),
                    _sql_literal(record.symbol),
                    _sql_literal(record.quantity),
                    _sql_literal(record.price),
                    _sql_literal(record.amount),
                    _sql_literal(record.currency),
                    _sql_literal(record.notes),
                ]
            )
            self._db.execute(
                f"INSERT INTO portfolio_transactions_log ({cols}) VALUES ({vals})"
            )

    def clear(self) -> None:
        super().clear()
        with self._persist_lock:
            self._db.execute("DELETE FROM portfolio_snapshots")
            # Transactions remain append-only — do not wipe durable ledger rows
            # on clear(); tests that need a clean ledger should use a fresh db.


def build_portfolio_store(database: Any | None = None) -> InMemoryPortfolioStore:
    """Factory — ``DatabasePort``-backed when provided, else in-memory."""
    if database is None:
        return InMemoryPortfolioStore()
    return DatabasePortfolioStore(database)


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("'", "''")
    return f"'{text}'"


def _decode_payload(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        decoded = base64.b64decode(raw.encode("ascii")).decode("utf-8")
        data = json.loads(decoded)
        if isinstance(data, dict):
            return data
    except Exception:  # noqa: BLE001
        pass
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _portfolio_from_dict(data: dict[str, Any]) -> Portfolio:
    return Portfolio(
        portfolio_id=str(data["portfolio_id"]),
        user_id=str(data["user_id"]),
        name=str(data["name"]),
        is_default=bool(data.get("is_default", False)),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        org_id=data.get("org_id"),
        benchmark_symbol=data.get("benchmark_symbol"),
        metadata=freeze_mapping(data.get("metadata")),
    )


def _holding_from_dict(data: dict[str, Any]) -> Holding:
    return Holding(
        holding_id=str(data["holding_id"]),
        portfolio_id=str(data["portfolio_id"]),
        symbol=str(data["symbol"]),
        weight=float(data["weight"]),
        created_at=str(data["created_at"]),
        updated_at=str(data["updated_at"]),
        units=data.get("units"),
        cost_basis_per_unit=data.get("cost_basis_per_unit"),
        purchase_date=data.get("purchase_date"),
        sector=data.get("sector"),
        country=data.get("country"),
        exchange=data.get("exchange"),
        value_score=data.get("value_score"),
        quality_score=data.get("quality_score"),
        momentum_score=data.get("momentum_score"),
        size_score=data.get("size_score"),
        volatility_score=data.get("volatility_score"),
    )


def _watchlist_item_from_dict(data: dict[str, Any]) -> WatchlistItem:
    return WatchlistItem(
        item_id=str(data["item_id"]),
        portfolio_id=str(data["portfolio_id"]),
        symbol=str(data["symbol"]),
        added_at=str(data["added_at"]),
        label=data.get("label"),
    )


def _num_or_none(raw: Any) -> float | None:
    if raw is None or raw == "" or raw == "NULL":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _transaction_from_row(row: dict[str, Any]) -> Transaction:
    return Transaction(
        transaction_id=str(row["transaction_id"]),
        portfolio_id=str(row["portfolio_id"]),
        transaction_type=str(row["transaction_type"]),
        transaction_date=str(row["transaction_date"]),
        created_at=str(row["created_at"]),
        symbol=row.get("symbol"),
        quantity=_num_or_none(row.get("quantity")),
        price=_num_or_none(row.get("price")),
        amount=_num_or_none(row.get("amount")),
        currency=str(row.get("currency") or "USD"),
        notes=row.get("notes"),
    )
