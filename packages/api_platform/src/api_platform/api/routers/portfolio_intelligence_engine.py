"""Portfolio Intelligence Engine routes (RC1 Milestone 4).

Stateless ``POST`` endpoints — the caller supplies portfolio holdings (and,
optionally, linked Research Objects) in the request body; every handler
only calls the matching ``state.platform.evaluate_portfolio_*`` method and
maps the result to a JSON envelope. No business logic here.

Mounted under ``/portfolio/insights`` — deliberately **not**
``/portfolio/intelligence``, which is already taken by the EPIC-A002
Portfolio Intelligence module (``portfolio_intelligence.py``, a distinct
capability: caller-supplied Research Object pass-through summaries, no
engine orchestration). See ``docs/PORTFOLIO_GUIDE.md`` §"Portfolio
Intelligence Engine" for the naming rationale.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["portfolio-intelligence-engine"])


class _EngineRequestBase(BaseModel):
    portfolio: dict[str, Any] | None = None
    research_objects: dict[str, Any] | list[Any] | None = None
    reports: dict[str, Any] | list[Any] | None = None
    snapshots: dict[str, Any] | list[Any] | None = None
    snapshot_ids: dict[str, str] | None = None
    benchmark_symbol: str | None = Field(None, max_length=32)
    window_days: int = Field(252, ge=5, le=3650)
    as_of: str | None = None


class PortfolioInsightsRequest(_EngineRequestBase):
    cash_weight: float | None = None
    stress_window_ids: list[str] | None = None


class PortfolioHealthRequest(_EngineRequestBase):
    cash_weight: float | None = None


class PortfolioRecommendationsRequest(_EngineRequestBase):
    pass


class PortfolioOpportunitiesRequest(_EngineRequestBase):
    pass


class PortfolioScenarioRequest(_EngineRequestBase):
    pass


def _error_response(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "ok": False,
            "available": False,
            "error": str(exc),
            "message": "Data unavailable.",
        },
    )


@router.post("/portfolio/insights")
def portfolio_insights(
    body: PortfolioInsightsRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Full Portfolio Intelligence Engine result — every capability at once."""
    try:
        result = state.platform.evaluate_portfolio_intelligence_engine(
            body.portfolio,
            research_objects=body.research_objects,
            reports=body.reports,
            snapshots=body.snapshots,
            snapshot_ids=body.snapshot_ids,
            benchmark_symbol=body.benchmark_symbol,
            window_days=body.window_days,
            cash_weight=body.cash_weight,
            stress_window_ids=body.stress_window_ids,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/insights/health")
def portfolio_insights_health(
    body: PortfolioHealthRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Portfolio Health Score — Diversification/Risk/Valuation/Quality/
    Concentration/Cash."""
    try:
        result = state.platform.evaluate_portfolio_health(
            body.portfolio,
            research_objects=body.research_objects,
            reports=body.reports,
            snapshots=body.snapshots,
            snapshot_ids=body.snapshot_ids,
            benchmark_symbol=body.benchmark_symbol,
            window_days=body.window_days,
            cash_weight=body.cash_weight,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/insights/recommendations")
def portfolio_insights_recommendations(
    body: PortfolioRecommendationsRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """AI Recommendations — rule-based Increase/Reduce/Hold/Review/Watch per holding."""
    try:
        result = state.platform.evaluate_portfolio_recommendations(
            body.portfolio,
            research_objects=body.research_objects,
            reports=body.reports,
            snapshots=body.snapshots,
            snapshot_ids=body.snapshot_ids,
            benchmark_symbol=body.benchmark_symbol,
            window_days=body.window_days,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/insights/opportunities")
def portfolio_insights_opportunities(
    body: PortfolioOpportunitiesRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Portfolio Opportunity Finder — ranking by MoS/Quality/Risk/Conviction."""
    try:
        result = state.platform.evaluate_portfolio_opportunities(
            body.portfolio,
            research_objects=body.research_objects,
            reports=body.reports,
            snapshots=body.snapshots,
            snapshot_ids=body.snapshot_ids,
            benchmark_symbol=body.benchmark_symbol,
            window_days=body.window_days,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/insights/scenario")
def portfolio_insights_scenario(
    body: PortfolioScenarioRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Portfolio AI Committee / Scenario Summary — Bull/Base/Bear synthesis."""
    try:
        result = state.platform.evaluate_portfolio_scenario(
            body.portfolio,
            research_objects=body.research_objects,
            reports=body.reports,
            snapshots=body.snapshots,
            snapshot_ids=body.snapshot_ids,
            benchmark_symbol=body.benchmark_symbol,
            window_days=body.window_days,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.get("/portfolio/insights/health-check")
def portfolio_insights_health_check(
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "health": state.platform.portfolio_intelligence_engine_health()}
