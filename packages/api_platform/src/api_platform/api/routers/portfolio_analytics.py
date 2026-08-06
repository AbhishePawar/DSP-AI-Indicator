"""Additive Portfolio Intelligence Analytics routes.

Stateless ``POST`` endpoints mirroring ``/portfolio/intelligence`` — the
caller supplies portfolio holdings in the request body; every handler only
calls the matching ``state.platform.evaluate_portfolio_*``/``*_health``
method and maps the result to a JSON envelope. No business logic here.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["portfolio-analytics"])


class _PortfolioRequestBase(BaseModel):
    portfolio: dict[str, Any] | None = None


class PerformanceRequest(_PortfolioRequestBase):
    benchmark_symbol: str | None = Field(None, max_length=32)
    window_days: int = Field(252, ge=5, le=3650)
    risk_free_rate: float = 0.0
    as_of: str | None = None


class RiskRequest(_PortfolioRequestBase):
    window_days: int = Field(252, ge=5, le=3650)
    as_of: str | None = None


class AllocationRequest(_PortfolioRequestBase):
    pass


class SimulationRequest(_PortfolioRequestBase):
    window_days: int = Field(252, ge=5, le=3650)
    monte_carlo_paths: int = Field(1000, ge=1, le=20000)
    monte_carlo_horizon_days: int = Field(252, ge=1, le=3650)
    frontier_samples: int = Field(200, ge=1, le=5000)
    seed: int | None = None
    as_of: str | None = None


class StressRequest(_PortfolioRequestBase):
    scenarios: list[dict[str, Any]] | None = None
    stress_window_ids: list[str] | None = None
    benchmark_symbol: str | None = Field(None, max_length=32)
    window_days: int = Field(252, ge=5, le=3650)
    as_of: str | None = None


class ConstraintsRequest(_PortfolioRequestBase):
    max_position_weight: float | None = None
    max_sector_weight: float | None = None
    sector_limits: dict[str, float] | None = None
    min_cash_weight: float | None = None
    cash_weight: float | None = None
    target_weights: dict[str, float] | None = None
    drift_threshold: float = 0.0


class TaxRequest(_PortfolioRequestBase):
    as_of: str | None = None


def _error_response(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"ok": False, "available": False, "error": str(exc), "message": "Data unavailable."},
    )


@router.post("/portfolio/analytics/performance")
def portfolio_analytics_performance(
    body: PerformanceRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Sharpe, Sortino, Treynor, Alpha, Beta, Tracking Error, Information Ratio, Max Drawdown."""
    try:
        result = state.platform.evaluate_portfolio_performance(
            body.portfolio,
            benchmark_symbol=body.benchmark_symbol,
            window_days=body.window_days,
            risk_free_rate=body.risk_free_rate,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/analytics/risk")
def portfolio_analytics_risk(
    body: RiskRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Risk Attribution, Factor Exposure, Correlation Matrix, Portfolio Heatmap."""
    try:
        result = state.platform.evaluate_portfolio_risk_analytics(
            body.portfolio, window_days=body.window_days, as_of=body.as_of
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/analytics/allocation")
def portfolio_analytics_allocation(
    body: AllocationRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Sector Allocation, Country Allocation."""
    try:
        result = state.platform.evaluate_portfolio_allocation_analytics(body.portfolio)
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/analytics/simulation")
def portfolio_analytics_simulation(
    body: SimulationRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Monte Carlo, Efficient Frontier."""
    try:
        result = state.platform.evaluate_portfolio_simulation(
            body.portfolio,
            window_days=body.window_days,
            monte_carlo_paths=body.monte_carlo_paths,
            monte_carlo_horizon_days=body.monte_carlo_horizon_days,
            frontier_samples=body.frontier_samples,
            seed=body.seed,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/analytics/stress")
def portfolio_analytics_stress(
    body: StressRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Scenario Analysis, Stress Testing."""
    try:
        result = state.platform.evaluate_portfolio_stress_analytics(
            body.portfolio,
            scenarios=body.scenarios,
            stress_window_ids=body.stress_window_ids,
            benchmark_symbol=body.benchmark_symbol,
            window_days=body.window_days,
            as_of=body.as_of,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/analytics/constraints")
def portfolio_analytics_constraints(
    body: ConstraintsRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Position Limits, Rebalancing — analysis only, never a trade order."""
    try:
        result = state.platform.evaluate_portfolio_constraints(
            body.portfolio,
            max_position_weight=body.max_position_weight,
            max_sector_weight=body.max_sector_weight,
            sector_limits=body.sector_limits,
            min_cash_weight=body.min_cash_weight,
            cash_weight=body.cash_weight,
            target_weights=body.target_weights,
            drift_threshold=body.drift_threshold,
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.post("/portfolio/analytics/tax")
def portfolio_analytics_tax(
    body: TaxRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Tax Optimization — unrealized gain/loss, holding period, loss harvesting."""
    try:
        result = state.platform.evaluate_portfolio_tax_analytics(
            body.portfolio, as_of=body.as_of
        )
    except Exception as exc:  # noqa: BLE001
        return _error_response(exc)
    return JSONResponse({"ok": True, **result})


@router.get("/portfolio/analytics/health")
def portfolio_analytics_health(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "health": state.platform.portfolio_analytics_health()}
