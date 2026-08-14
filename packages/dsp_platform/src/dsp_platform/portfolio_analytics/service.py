"""Portfolio Analytics façade service (Portfolio Intelligence Analytics Module).

Stateless dict-in/dict-out contract — mirrors ``dsp_platform.portfolio_intelligence``
(EPIC-A002): the caller supplies portfolio holdings in the request body, this
module resolves price history via ``HistoricalSeriesPriceHistoryAdapter``
(reusing ``dsp_platform.historical_series``), builds ``portfolio_analytics``
domain inputs, and calls the pure engine. Every public function returns an
honest dict — ``None``/``"Data unavailable."`` per field when history,
benchmark, or cost-basis inputs are missing. No valuation, scoring, or
provider integration happens here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from threading import Lock
from typing import Any

from dsp_platform.portfolio_analytics.adapter import HistoricalSeriesPriceHistoryAdapter
from portfolio_analytics import (
    DailyReturn,
    PositionInput,
    align_return_series,
    check_position_limits,
    compute_beta,
    compute_country_allocation,
    compute_efficient_frontier,
    compute_factor_exposures,
    compute_monte_carlo,
    compute_performance_ratios,
    compute_rebalancing_plan,
    compute_risk_attribution,
    compute_scenario_impact,
    compute_sector_allocation,
    compute_stress_test,
    compute_tax_report,
    cumulative_window_return,
    weighted_series,
)

__all__ = [
    "PORTFOLIO_ANALYTICS_SERVICE_VERSION",
    "STRESS_WINDOW_CATALOG",
    "evaluate_portfolio_allocation_analytics",
    "evaluate_portfolio_constraints",
    "evaluate_portfolio_performance",
    "evaluate_portfolio_risk_analytics",
    "evaluate_portfolio_simulation",
    "evaluate_portfolio_stress_analytics",
    "evaluate_portfolio_tax_analytics",
    "parse_positions",
    "portfolio_analytics_health",
    "portfolio_analytics_metrics",
    "set_price_history_adapter_for_tests",
]

_LOCK = Lock()
_ADAPTER_OVERRIDE: HistoricalSeriesPriceHistoryAdapter | None = None

PORTFOLIO_ANALYTICS_SERVICE_VERSION = "1.0.0"

#: Predefined historical crash windows for Stress Testing. Intentionally
#: small and explicit — an unrecognised ``window_id`` yields an honest error,
#: never a guessed date range.
STRESS_WINDOW_CATALOG: dict[str, tuple[date, date, str]] = {
    "gfc_2008": (date(2008, 9, 1), date(2009, 3, 9), "2008 Global Financial Crisis"),
    "covid_2020": (date(2020, 2, 19), date(2020, 3, 23), "2020 COVID-19 crash"),
}

_DEFAULT_WINDOW_DAYS = 252
_DEFAULT_RISK_FREE_RATE = 0.0


def _adapter() -> HistoricalSeriesPriceHistoryAdapter:
    with _LOCK:
        if _ADAPTER_OVERRIDE is not None:
            return _ADAPTER_OVERRIDE
    return HistoricalSeriesPriceHistoryAdapter()


def set_price_history_adapter_for_tests(
    adapter: HistoricalSeriesPriceHistoryAdapter | None,
) -> None:
    """Inject a fake ``PriceHistoryPort`` implementation (tests only)."""
    global _ADAPTER_OVERRIDE
    with _LOCK:
        _ADAPTER_OVERRIDE = adapter


def _to_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _holdings(portfolio: Mapping[str, Any] | None) -> tuple[Mapping[str, Any], ...]:
    if not portfolio:
        return ()
    holdings = portfolio.get("holdings")
    if not isinstance(holdings, (list, tuple)):
        return ()
    return tuple(h for h in holdings if isinstance(h, Mapping))


def parse_positions(portfolio: Mapping[str, Any] | None) -> tuple[PositionInput, ...]:
    """Parse the caller's stateless ``{"holdings": [...]}`` payload."""
    positions: list[PositionInput] = []
    for row in _holdings(portfolio):
        symbol = row.get("symbol") or row.get("ticker")
        weight = row.get("weight")
        if not symbol or weight is None:
            continue
        positions.append(
            PositionInput(
                symbol=str(symbol),
                weight=float(weight),
                units=(
                    float(row["units"]) if row.get("units") is not None else None
                ),
                cost_basis_per_unit=(
                    float(row["cost_basis_per_unit"])
                    if row.get("cost_basis_per_unit") is not None
                    else None
                ),
                purchase_date=_to_date(row.get("purchase_date")),
                sector=row.get("sector"),
                country=row.get("country"),
                exchange=row.get("exchange"),
                value_score=(
                    float(row["value_score"])
                    if row.get("value_score") is not None
                    else None
                ),
                quality_score=(
                    float(row["quality_score"])
                    if row.get("quality_score") is not None
                    else None
                ),
                momentum_score=(
                    float(row["momentum_score"])
                    if row.get("momentum_score") is not None
                    else None
                ),
                size_score=(
                    float(row["size_score"])
                    if row.get("size_score") is not None
                    else None
                ),
                volatility_score=(
                    float(row["volatility_score"])
                    if row.get("volatility_score") is not None
                    else None
                ),
            )
        )
    return tuple(positions)


def _fetch_returns(
    symbols: Sequence[str],
    *,
    start: date | None,
    end: date | None,
) -> dict[str, tuple[DailyReturn, ...] | None]:
    adapter = _adapter()
    return {
        symbol: adapter.get_daily_returns(symbol, start=start, end=end)
        for symbol in symbols
    }


def _window(window_days: int, *, as_of: date | str | None = None) -> tuple[date, date]:
    end = _to_date(as_of) or date.today()
    start = end - timedelta(days=int(window_days * 1.6) + 10)  # buffer for non-trading days
    return start, end


def _weights_map(positions: Sequence[PositionInput]) -> dict[str, float]:
    return {p.symbol: p.weight for p in positions}


def evaluate_portfolio_performance(
    portfolio: Mapping[str, Any] | None,
    *,
    benchmark_symbol: str | None = None,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    risk_free_rate: float = _DEFAULT_RISK_FREE_RATE,
    as_of: date | str | None = None,
) -> dict[str, Any]:
    positions = parse_positions(portfolio)
    if not positions:
        return {
            "available": False,
            "message": "Data unavailable.",
            "result": None,
            "limitations": ("no portfolio holdings supplied.",),
        }

    start, end = _window(window_days, as_of=as_of)
    symbols = [p.symbol for p in positions]
    returns_by_symbol = _fetch_returns(symbols, start=start, end=end)
    aligned = align_return_series(returns_by_symbol)
    if aligned is None:
        return {
            "available": False,
            "message": "Data unavailable.",
            "result": None,
            "limitations": (
                "no overlapping authenticated price history across the "
                "supplied holdings.",
            ),
        }

    portfolio_returns = weighted_series(_weights_map(positions), aligned)
    if portfolio_returns is None:
        return {
            "available": False,
            "message": "Data unavailable.",
            "result": None,
            "limitations": ("supplied weights sum to zero.",),
        }

    benchmark_returns: tuple[float, ...] | None = None
    if benchmark_symbol:
        benchmark_series = _adapter().get_daily_returns(
            benchmark_symbol, start=start, end=end
        )
        if benchmark_series:
            joint = align_return_series(
                {"__portfolio__": tuple(
                    DailyReturn(trade_date=d, return_value=r)
                    for d, r in zip(aligned.dates, portfolio_returns, strict=True)
                ), "__benchmark__": benchmark_series}
            )
            if joint is not None:
                portfolio_returns = joint.series["__portfolio__"]
                benchmark_returns = joint.series["__benchmark__"]

    result = compute_performance_ratios(
        portfolio_returns,
        benchmark_returns,
        risk_free_rate=risk_free_rate,
    )
    return {
        "available": True,
        "message": None,
        "result": result.to_public_dict(),
        "benchmark_symbol": benchmark_symbol,
    }


def evaluate_portfolio_risk_analytics(
    portfolio: Mapping[str, Any] | None,
    *,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    as_of: date | str | None = None,
) -> dict[str, Any]:
    positions = parse_positions(portfolio)
    if not positions:
        return {
            "available": False,
            "message": "Data unavailable.",
            "risk_attribution": None,
            "factor_exposure": None,
        }

    start, end = _window(window_days, as_of=as_of)
    symbols = [p.symbol for p in positions]
    returns_by_symbol = _fetch_returns(symbols, start=start, end=end)
    weights = _weights_map(positions)
    sectors = {p.symbol: p.sector for p in positions}

    aligned = align_return_series(returns_by_symbol)
    portfolio_returns: tuple[float, ...] = ()
    if aligned is not None:
        blended = weighted_series(weights, aligned)
        if blended is not None:
            portfolio_returns = blended

    risk_attribution = compute_risk_attribution(
        weights=weights,
        sectors=sectors,
        returns_by_symbol=returns_by_symbol,
        portfolio_returns=portfolio_returns,
    )
    factor_exposure = compute_factor_exposures(positions)

    return {
        "available": True,
        "message": None,
        "risk_attribution": risk_attribution.to_public_dict(),
        "factor_exposure": factor_exposure.to_public_dict(),
    }


def evaluate_portfolio_allocation_analytics(
    portfolio: Mapping[str, Any] | None,
) -> dict[str, Any]:
    positions = parse_positions(portfolio)
    if not positions:
        return {
            "available": False,
            "message": "Data unavailable.",
            "sector_allocation": None,
            "country_allocation": None,
        }

    return {
        "available": True,
        "message": None,
        "sector_allocation": compute_sector_allocation(positions).to_public_dict(),
        "country_allocation": compute_country_allocation(positions).to_public_dict(),
    }


def evaluate_portfolio_simulation(
    portfolio: Mapping[str, Any] | None,
    *,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    monte_carlo_paths: int = 1000,
    monte_carlo_horizon_days: int = 252,
    frontier_samples: int = 200,
    seed: int | None = None,
    as_of: date | str | None = None,
) -> dict[str, Any]:
    positions = parse_positions(portfolio)
    if not positions:
        return {
            "available": False,
            "message": "Data unavailable.",
            "monte_carlo": None,
            "efficient_frontier": None,
        }

    start, end = _window(window_days, as_of=as_of)
    symbols = [p.symbol for p in positions]
    returns_by_symbol = _fetch_returns(symbols, start=start, end=end)
    aligned = align_return_series(returns_by_symbol)

    weights = _weights_map(positions)
    portfolio_returns: tuple[float, ...] = ()
    if aligned is not None:
        blended = weighted_series(weights, aligned)
        if blended is not None:
            portfolio_returns = blended

    monte_carlo = compute_monte_carlo(
        portfolio_returns,
        paths=monte_carlo_paths,
        horizon_days=monte_carlo_horizon_days,
        seed=seed,
    )

    if aligned is not None:
        frontier = compute_efficient_frontier(
            aligned,
            current_weights=weights,
            samples=frontier_samples,
            seed=seed,
        )
    else:
        from portfolio_analytics.enums import AnalyticsStatus
        from portfolio_analytics.models import EfficientFrontierResult

        frontier = EfficientFrontierResult(
            status=AnalyticsStatus.UNAVAILABLE,
            points=(),
            current_portfolio_point=None,
            method_id="dsp.portfolio_analytics.method.efficient_frontier.random_weight_sampling.v1",
            samples=frontier_samples,
            limitations=("no overlapping authenticated price history.",),
        )

    return {
        "available": True,
        "message": None,
        "monte_carlo": monte_carlo.to_public_dict(),
        "efficient_frontier": frontier.to_public_dict(),
    }


def evaluate_portfolio_stress_analytics(
    portfolio: Mapping[str, Any] | None,
    *,
    scenarios: Sequence[Mapping[str, Any]] | None = None,
    stress_window_ids: Sequence[str] | None = None,
    benchmark_symbol: str | None = None,
    window_days: int = _DEFAULT_WINDOW_DAYS,
    as_of: date | str | None = None,
) -> dict[str, Any]:
    positions = parse_positions(portfolio)
    if not positions:
        return {
            "available": False,
            "message": "Data unavailable.",
            "scenarios": [],
            "stress_tests": [],
        }

    start, end = _window(window_days, as_of=as_of)
    symbols = [p.symbol for p in positions]
    returns_by_symbol = _fetch_returns(symbols, start=start, end=end)

    betas: dict[str, float | None] = {}
    if benchmark_symbol:
        benchmark_series = _adapter().get_daily_returns(
            benchmark_symbol, start=start, end=end
        )
        for symbol, series in returns_by_symbol.items():
            if series is None or benchmark_series is None:
                betas[symbol] = None
                continue
            joint = align_return_series({"__p__": series, "__b__": benchmark_series})
            betas[symbol] = (
                compute_beta(joint.series["__p__"], joint.series["__b__"])
                if joint is not None
                else None
            )
    else:
        betas = dict.fromkeys(symbols)

    scenario_results = [
        compute_scenario_impact(
            str(row.get("name", "scenario")),
            float(row.get("shock_pct", 0.0)),
            positions=positions,
            betas=betas,
            default_beta=float(row.get("default_beta", 1.0)),
        ).to_public_dict()
        for row in (scenarios or [])
    ]

    stress_results = []
    for window_id in stress_window_ids or ():
        window = STRESS_WINDOW_CATALOG.get(window_id)
        if window is None:
            stress_results.append(
                {
                    "scenario_id": window_id,
                    "available": False,
                    "message": f"Unknown stress window id: {window_id!r}.",
                }
            )
            continue
        window_start, window_end, description = window
        window_symbols = [*symbols]
        if benchmark_symbol:
            window_symbols.append(benchmark_symbol)
        window_returns = _fetch_returns(
            window_symbols, start=window_start, end=window_end
        )
        benchmark_shock_pct = None
        if benchmark_symbol:
            benchmark_shock_pct = cumulative_window_return(
                window_returns.get(benchmark_symbol),
                window_start=window_start,
                window_end=window_end,
            )
        result = compute_stress_test(
            scenario_id=window_id,
            description=description,
            window_start=window_start,
            window_end=window_end,
            positions=positions,
            returns_by_symbol={s: window_returns.get(s) for s in symbols},
            betas=betas,
            benchmark_shock_pct=benchmark_shock_pct,
        )
        stress_results.append({"available": True, **result.to_public_dict()})

    return {
        "available": True,
        "message": None,
        "scenarios": scenario_results,
        "stress_tests": stress_results,
        "stress_window_catalog": {
            window_id: {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "description": description,
            }
            for window_id, (start_date, end_date, description) in STRESS_WINDOW_CATALOG.items()
        },
    }


def evaluate_portfolio_constraints(
    portfolio: Mapping[str, Any] | None,
    *,
    max_position_weight: float | None = None,
    max_sector_weight: float | None = None,
    sector_limits: Mapping[str, float] | None = None,
    min_cash_weight: float | None = None,
    cash_weight: float | None = None,
    target_weights: Mapping[str, float] | None = None,
    drift_threshold: float = 0.0,
) -> dict[str, Any]:
    positions = parse_positions(portfolio)
    limits_report = check_position_limits(
        positions,
        max_position_weight=max_position_weight,
        max_sector_weight=max_sector_weight,
        sector_limits=sector_limits,
        min_cash_weight=min_cash_weight,
        cash_weight=cash_weight,
    )
    rebalancing_plan = compute_rebalancing_plan(
        positions, target_weights or {}, drift_threshold=drift_threshold
    )
    return {
        "available": True,
        "message": None,
        "position_limits": limits_report.to_public_dict(),
        "rebalancing": rebalancing_plan.to_public_dict(),
    }


def evaluate_portfolio_tax_analytics(
    portfolio: Mapping[str, Any] | None,
    *,
    as_of: date | str | None = None,
) -> dict[str, Any]:
    positions = parse_positions(portfolio)
    if not positions:
        return {
            "available": False,
            "message": "Data unavailable.",
            "result": None,
        }

    as_of_date = _to_date(as_of) or date.today()
    current_prices: dict[str, float] = {}
    for position in positions:
        # Tax analytics needs an actual price level, not a return series, so
        # query the raw historical bundle directly (still via the reused
        # ``historical_series`` façade — no new provider integration).
        price = _latest_close(position.symbol, as_of=as_of_date)
        if price is not None:
            current_prices[position.symbol] = price

    report = compute_tax_report(positions, current_prices=current_prices, as_of=as_of_date)
    return {"available": True, "message": None, "result": report.to_public_dict()}


def _latest_close(symbol: str, *, as_of: date) -> float | None:
    from dsp_platform.historical_series import get_authenticated_historical_series

    payload = get_authenticated_historical_series(
        symbol, series_kind="ohlcv", frequency="daily", end_date=as_of, limit=5
    )
    if payload is None:
        return None
    bars = payload.get("bars") or []
    closes = [b.get("close") for b in bars if b.get("close") is not None]
    if not closes:
        return None
    return float(closes[-1])


def portfolio_analytics_health() -> dict[str, Any]:
    from dsp_platform.historical_series import historical_series_health

    return {
        "service_version": PORTFOLIO_ANALYTICS_SERVICE_VERSION,
        "price_history_source": historical_series_health(),
    }


def portfolio_analytics_metrics() -> dict[str, Any]:
    from dsp_platform.historical_series import historical_series_metrics

    return {"price_history_source": historical_series_metrics()}
