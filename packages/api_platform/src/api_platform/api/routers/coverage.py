"""Coverage registry routes — Figma Institutional Research · Company Directory ·
Research Intelligence signal feed.

Read-only aggregates over server-authored ``/analyse`` records. No engines,
no providers, no derived scores: counts, copies and two-record comparisons.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_authenticated_actor,
)

router = APIRouter(tags=["coverage"])


class CoverageStatsModel(BaseModel):
    securities_covered: int
    dsp_rated: int
    a_rated: int
    a_plus_rated: int
    last_updated: str | None = None


class ScreenerRowModel(BaseModel):
    symbol: str
    company_name: str | None = None
    rating: str | None = None
    business_quality_score: float | None = None
    sector: str | None = None
    pe: float | None = None
    roe: float | None = None
    roce: float | None = None
    revenue_growth: float | None = None
    fcf: float | None = None
    price: float | None = None
    market_cap: float | None = None
    as_of: str
    research_id: str | None = None


class InstitutionalResponse(BaseModel):
    ok: bool
    stats: CoverageStatsModel
    screener: list[ScreenerRowModel]
    coverage_growth: list[dict[str, Any]]
    rating_distribution: list[dict[str, Any]]
    sectors: list[str]
    message: str | None = None


class DirectoryItemModel(BaseModel):
    symbol: str
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    rating: str | None = None
    price: float | None = None
    change: float | None = None
    change_percent: float | None = None
    as_of: str | None = None


class DirectoryResponse(BaseModel):
    ok: bool
    items: list[DirectoryItemModel]
    count: int
    limit: int = 48
    offset: int = 0
    sectors: list[str]


class CompareResponse(BaseModel):
    ok: bool
    available: bool
    a: dict[str, Any] | None = None
    b: dict[str, Any] | None = None
    metrics: list[dict[str, Any]]
    radar: dict[str, Any]
    formula: dict[str, str]
    message: str | None = None


class SignalItemModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    symbol: str
    type: str
    timestamp: str
    company_name: str | None = None
    sector: str | None = None
    label: str | None = None
    severity: str | None = None
    status: str | None = None
    source: str | None = None
    dsp_context: dict[str, Any] | None = None
    research_id: str | None = None
    text: str | None = None


class TodaySummaryModel(BaseModel):
    new_signals: int
    upgrades: int
    downgrades: int
    risk_flags: int
    as_of: str


class SignalsResponse(BaseModel):
    ok: bool
    signals: list[SignalItemModel]
    today: TodaySummaryModel
    sectors: list[str]
    count: int


@router.get("/coverage/institutional")
def institutional_overview(
    request: Request,
    state: ApiState = Depends(get_api_state),
    rating: str | None = Query(None, max_length=4),
    months: int = Query(6, ge=1, le=24),
) -> InstitutionalResponse:
    """Stats · Quality Screener · Coverage Growth · Rating Distribution."""
    require_authenticated_actor(request)
    registry = state.platform.coverage_registry()
    stats = registry.stats()
    return InstitutionalResponse.model_validate(
        {
            "ok": True,
            "stats": stats,
            "screener": registry.screener(rating),
            "coverage_growth": registry.coverage_growth(months),
            "rating_distribution": registry.rating_distribution(),
            "sectors": registry.sectors(),
            "message": None
            if stats["securities_covered"]
            else "Data unavailable. No securities have been analysed yet.",
        }
    )


@router.get("/coverage/directory")
def company_directory(
    request: Request,
    state: ApiState = Depends(get_api_state),
    sector: str | None = Query(None, max_length=120),
    rating: str | None = Query(None, max_length=8),
    q: str | None = Query(None, max_length=64),
    sort: Literal["symbol", "rating", "sector", "market_cap", "price"] = Query("symbol"),
    order: Literal["asc", "desc"] = Query("asc"),
    limit: int = Query(48, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> DirectoryResponse:
    require_authenticated_actor(request)
    registry = state.platform.coverage_registry()
    page = registry.directory_page(
        sector=sector, rating=rating, q=q, sort=sort, order=order, limit=limit, offset=offset
    )
    for item in page["items"]:
        try:
            quote = state.platform.get_authenticated_market_quote(
                item["symbol"], exchange=item.get("exchange"), currency="INR"
            )
        except Exception:  # noqa: BLE001 — provider failure stays unavailable
            quote = None
        fields = quote.get("fields") if isinstance(quote, dict) else None
        fields = fields if isinstance(fields, dict) else {}
        if fields.get("current_price") is not None:
            item["price"] = fields.get("current_price")
        item["change"] = fields.get("change")
        item["change_percent"] = fields.get("change_percent")
    return DirectoryResponse.model_validate({"ok": True, **page})


@router.get("/coverage/compare")
def coverage_compare(
    request: Request,
    state: ApiState = Depends(get_api_state),
    a: str = Query(..., min_length=1, max_length=32),
    b: str = Query(..., min_length=1, max_length=32),
) -> CompareResponse:
    require_authenticated_actor(request)
    return CompareResponse.model_validate(state.platform.coverage_registry().compare(a, b))


@router.get("/coverage/signals")
def coverage_signals(
    request: Request,
    state: ApiState = Depends(get_api_state),
    limit: int = Query(50, ge=1, le=500),
    symbol: str | None = Query(None, max_length=32),
    type: str | None = Query(None, max_length=16),  # noqa: A002 — API field name
    sector: str | None = Query(None, max_length=120),
) -> SignalsResponse:
    require_authenticated_actor(request)
    registry = state.platform.coverage_registry()
    signals = registry.signals(limit=limit if not (type or sector) else 10_000, symbol=symbol)
    if type and type.lower() != "all":
        signals = [s for s in signals if s["type"] == type.lower()]
    if sector and sector.lower() != "all":
        signals = [s for s in signals if (s.get("sector") or "").lower() == sector.lower()]
    signals = signals[:limit]
    return SignalsResponse.model_validate(
        {
            "ok": True,
            "signals": signals,
            "today": registry.today_summary(),
            "sectors": registry.sectors(),
            "count": len(signals),
        }
    )


@router.get("/coverage/latest/{symbol}")
def coverage_latest(
    symbol: str, request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    require_authenticated_actor(request)
    latest = state.platform.coverage_registry().latest(symbol)
    return {"ok": True, "available": latest is not None, "record": latest}
