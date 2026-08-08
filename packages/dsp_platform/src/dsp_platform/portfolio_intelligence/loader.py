"""Portfolio / watchlist loaders (EPIC-A002)."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from dsp_platform.portfolio_intelligence.models import Holding, Portfolio, Watchlist

__all__ = ["load_portfolio", "load_watchlist"]


def _norm_symbol(value: Any) -> str:
    return str(value or "").strip().upper()


def load_portfolio(data: Mapping[str, Any] | None) -> Portfolio | None:
    if not isinstance(data, Mapping):
        return None
    holdings_raw = data.get("holdings") or []
    holdings: list[Holding] = []
    if isinstance(holdings_raw, list):
        for row in holdings_raw:
            if not isinstance(row, Mapping):
                continue
            symbol = _norm_symbol(row.get("symbol") or row.get("ticker"))
            if not symbol:
                continue
            weight = row.get("weight")
            shares = row.get("shares")
            labels = row.get("labels") if isinstance(row.get("labels"), Mapping) else {}
            holdings.append(
                Holding(
                    symbol=symbol,
                    weight=float(weight) if isinstance(weight, (int, float)) else None,
                    shares=float(shares) if isinstance(shares, (int, float)) else None,
                    labels=dict(labels),
                )
            )
    # Deterministic holding order by symbol
    holdings.sort(key=lambda h: h.symbol)
    meta = data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {}
    return Portfolio(
        portfolio_id=str(data.get("portfolio_id") or uuid4()),
        name=data.get("name"),
        holdings=tuple(holdings),
        created_at=data.get("created_at"),
        metadata=dict(meta),
    )


def load_watchlist(data: Mapping[str, Any] | None) -> Watchlist | None:
    if not isinstance(data, Mapping):
        return None
    symbols_raw = data.get("symbols") or []
    symbols: list[str] = []
    if isinstance(symbols_raw, list):
        for item in symbols_raw:
            if isinstance(item, Mapping):
                sym = _norm_symbol(item.get("symbol") or item.get("ticker"))
            else:
                sym = _norm_symbol(item)
            if sym and sym not in symbols:
                symbols.append(sym)
    symbols.sort()
    meta = data.get("metadata") if isinstance(data.get("metadata"), Mapping) else {}
    return Watchlist(
        watchlist_id=str(data.get("watchlist_id") or uuid4()),
        name=data.get("name"),
        symbols=tuple(symbols),
        created_at=data.get("created_at"),
        metadata=dict(meta),
    )
