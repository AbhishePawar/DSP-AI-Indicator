"""Investor workspace read models (Figma Dashboard · Portfolio · Client Profile).

Joins user-authored records (watchlist, holdings, profile) with:

- authenticated market quotes (CMP, change, change %) — provider values only
- the coverage registry (DSP rating, sector, company name) — copied, not scored

Portfolio arithmetic performed here (and only here — never in the browser):
    invested      = quantity × average_cost
    current_value = quantity × cmp
    pnl           = current_value − invested
    return_pct    = pnl ÷ invested
    weight        = current_value ÷ Σ current_value

A holding whose CMP is unavailable contributes ``None`` to value / P&L and is
excluded from totals; the totals then report ``complete = False`` (CV-005).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from dsp_platform.coverage_registry.service import (
    CoverageRegistryService,
    get_coverage_registry_service,
)
from dsp_platform.investor_workspace.financial_health import (
    compute_financial_health,
    profile_completeness,
)
from dsp_platform.investor_workspace.store import (
    InvestorWorkspaceStore,
    get_investor_workspace_store,
)

__all__ = ["InvestorWorkspaceService", "get_investor_workspace_service"]

QuoteFetcher = Callable[[str, str | None], Mapping[str, Any] | None]


def _default_quote_fetcher(symbol: str, exchange: str | None) -> Mapping[str, Any] | None:
    from dsp_platform.market_quotes import get_authenticated_market_quote

    try:
        return get_authenticated_market_quote(symbol, exchange=exchange, currency="INR")
    except Exception:  # noqa: BLE001 — provider failure → unavailable, never fabricated
        return None


def _quote_fields(quote: Mapping[str, Any] | None) -> dict[str, Any]:
    fields = quote.get("fields") if isinstance(quote, Mapping) else None
    fields = fields if isinstance(fields, Mapping) else {}
    return {
        "price": fields.get("current_price"),
        "change": fields.get("change"),
        "change_percent": fields.get("change_percent"),
        "previous_close": fields.get("previous_close"),
        "currency": quote.get("currency") if isinstance(quote, Mapping) else None,
        "provenance": quote.get("provenance") if isinstance(quote, Mapping) else None,
        "available": fields.get("current_price") is not None,
    }


class InvestorWorkspaceService:
    def __init__(
        self,
        store: InvestorWorkspaceStore | None = None,
        *,
        coverage: CoverageRegistryService | None = None,
        quote_fetcher: QuoteFetcher | None = None,
    ) -> None:
        self._store = store or get_investor_workspace_store()
        self._coverage = coverage or get_coverage_registry_service()
        self._quotes = quote_fetcher or _default_quote_fetcher

    @property
    def store(self) -> InvestorWorkspaceStore:
        return self._store

    # -- watchlist ---------------------------------------------------------
    def watchlist_view(self, user_id: str) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for item in self._store.list_watchlist(user_id):
            quote = _quote_fields(self._quotes(item["symbol"], item.get("exchange")))
            latest = self._coverage.latest(item["symbol"]) or {}
            rows.append(
                {
                    "symbol": item["symbol"],
                    "exchange": item.get("exchange"),
                    "company_name": latest.get("company_name"),
                    "sector": latest.get("sector"),
                    "rating": latest.get("rating"),
                    "business_quality_score": latest.get("business_quality_score"),
                    "rated_at": latest.get("as_of"),
                    "quote": quote,
                    "added_at": item.get("added_at"),
                }
            )
        return {"ok": True, "items": rows, "count": len(rows)}

    # -- portfolio ---------------------------------------------------------
    def portfolio_view(self, user_id: str) -> dict[str, Any]:
        holdings = self._store.list_holdings(user_id)
        rows: list[dict[str, Any]] = []
        total_invested = 0.0
        total_current = 0.0
        priced = 0
        for h in holdings:
            qty = float(h["quantity"])
            avg = float(h["average_cost"])
            invested = qty * avg
            total_invested += invested
            quote = _quote_fields(self._quotes(h["symbol"], h.get("exchange")))
            latest = self._coverage.latest(h["symbol"]) or {}
            cmp_price = quote["price"]
            current_value = pnl = return_pct = None
            if cmp_price is not None:
                current_value = qty * float(cmp_price)
                pnl = current_value - invested
                return_pct = pnl / invested if invested > 0 else None
                total_current += current_value
                priced += 1
            rows.append(
                {
                    "holding_id": h["holding_id"],
                    "symbol": h["symbol"],
                    "exchange": h.get("exchange"),
                    "company_name": latest.get("company_name"),
                    "sector": h.get("sector_override") or latest.get("sector"),
                    "rating": latest.get("rating"),
                    "business_quality_score": latest.get("business_quality_score"),
                    "quantity": qty,
                    "average_cost": avg,
                    "invested": invested,
                    "cmp": cmp_price,
                    "current_value": current_value,
                    "pnl": pnl,
                    "return_pct": return_pct,
                    "weight": None,
                    "quote": quote,
                    "updated_at": h.get("updated_at"),
                }
            )
        complete = priced == len(rows)
        for row in rows:
            if row["current_value"] is not None and total_current > 0:
                row["weight"] = row["current_value"] / total_current

        sector_alloc: dict[str, float] = {}
        unclassified = 0.0
        for row in rows:
            if row["current_value"] is None:
                continue
            if row["sector"]:
                sector_alloc[row["sector"]] = sector_alloc.get(row["sector"], 0.0) + row["current_value"]
            else:
                unclassified += row["current_value"]
        allocation = [
            {"sector": sector, "value": value, "weight": value / total_current if total_current else None}
            for sector, value in sorted(sector_alloc.items(), key=lambda kv: -kv[1])
        ]
        if unclassified > 0:
            allocation.append(
                {"sector": None, "value": unclassified, "weight": unclassified / total_current if total_current else None}
            )

        summary: dict[str, Any] = {
            "holdings": len(rows),
            "priced_holdings": priced,
            "complete": complete,
            "total_invested": total_invested if rows else 0.0,
            "current_value": total_current if complete and rows else None,
            "total_pnl": (total_current - total_invested) if complete and rows else None,
            "return_pct": (
                (total_current - total_invested) / total_invested
                if complete and rows and total_invested > 0
                else None
            ),
            "formula": {
                "invested": "quantity × average_cost",
                "current_value": "quantity × cmp",
                "pnl": "current_value − invested",
                "return_pct": "pnl ÷ invested",
                "weight": "current_value ÷ Σ current_value",
            },
        }
        return {
            "ok": True,
            "summary": summary,
            "holdings": rows,
            "sector_allocation": allocation,
            "message": None if complete else "Data unavailable. One or more holdings have no authenticated price.",
        }

    # -- dashboard ---------------------------------------------------------
    def dashboard_overview(self, user_id: str) -> dict[str, Any]:
        watchlist = self.watchlist_view(user_id)["items"]
        seen = {item["symbol"] for item in watchlist}
        # Owner-analysed symbols that are not yet on the watchlist still appear
        # on the Figma Dashboard watchlist (same as session-derived rows).
        for rec in self._coverage.recent_research(user_id, limit=8):
            symbol = rec["symbol"]
            if symbol in seen:
                continue
            latest = self._coverage.latest(symbol) or {}
            quote = _quote_fields(self._quotes(symbol, latest.get("exchange")))
            watchlist.append(
                {
                    "symbol": symbol,
                    "exchange": latest.get("exchange"),
                    "company_name": rec.get("company_name") or latest.get("company_name"),
                    "sector": latest.get("sector"),
                    "rating": rec.get("rating") or latest.get("rating"),
                    "business_quality_score": latest.get("business_quality_score"),
                    "rated_at": rec.get("timestamp"),
                    "quote": quote,
                    "added_at": rec.get("timestamp"),
                    "origin": "research",
                }
            )
            seen.add(symbol)
        for item in watchlist:
            item.setdefault("origin", "watchlist")
        return {
            "ok": True,
            "watchlist": watchlist,
            "recent_research": self._coverage.recent_research(user_id, limit=8),
            "signals": self._coverage.signals(limit=8),
        }

    # -- client financial profile ------------------------------------------
    def profile_view(self, user_id: str, *, account: Mapping[str, Any] | None = None) -> dict[str, Any]:
        profile = self._store.get_profile(user_id)
        merged = dict(profile or {})
        # Locked "From your account" fields come from the authenticated user.
        if account:
            for src, dst in (("name", "full_name"), ("full_name", "full_name"), ("email", "email"), ("mobile", "mobile"), ("phone", "mobile")):
                if account.get(src) and not merged.get(dst):
                    merged[dst] = account[src]
        return {
            "ok": True,
            "profile": merged or None,
            "completeness": profile_completeness(merged),
            "health": compute_financial_health(merged),
        }

    def save_profile(self, user_id: str, profile: dict[str, Any], *, account: Mapping[str, Any] | None = None) -> dict[str, Any]:
        self._store.put_profile(user_id, profile)
        return self.profile_view(user_id, account=account)


_SERVICE: InvestorWorkspaceService | None = None


def get_investor_workspace_service() -> InvestorWorkspaceService:
    global _SERVICE
    store = get_investor_workspace_store()
    if _SERVICE is None or _SERVICE.store is not store:
        _SERVICE = InvestorWorkspaceService(store)
    return _SERVICE
