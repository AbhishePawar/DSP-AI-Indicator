"""Portfolio Intelligence Engine — orchestration (RC1 Milestone 4).

This is the **only** place where engine calls happen for this capability.
It combines:

- ``dsp_platform.portfolio_analytics`` (frozen, RC1 Milestone 1) for every
  quantitative number: performance ratios, risk attribution (including
  per-holding volatility/risk contribution), Monte Carlo, stress tests.
- ``dsp_platform.portfolio_intelligence.linker`` (frozen, EPIC-A002) for
  pass-through valuation/quality/committee signals from caller-linked
  Research Objects — reusing the exact same ``link_research_map`` /
  ``extract_field`` / ``section_available`` utilities EPIC-A002 itself uses,
  so no JSON-path traversal logic is duplicated.
- ``portfolio_intelligence_engine`` (new, pure combination/scoring package)
  for every Health Score / Concentration / Valuation Heatmap / Risk Summary
  / Recommendations / Drift / Diversification / Opportunities / Scenario
  calculation.

No valuation, risk, or AI computation happens in this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import portfolio_intelligence_engine as pie
from dsp_platform.portfolio_analytics import (
    evaluate_portfolio_performance,
    evaluate_portfolio_risk_analytics,
    evaluate_portfolio_simulation,
    evaluate_portfolio_stress_analytics,
)
from dsp_platform.portfolio_intelligence.linker import (
    ResearchBundle,
    extract_field,
    link_research_map,
    section_available,
)
from dsp_platform.portfolio_intelligence.models import UNAVAILABLE_MESSAGE

__all__ = [
    "PORTFOLIO_INTELLIGENCE_ENGINE_SERVICE_VERSION",
    "evaluate_portfolio_health",
    "evaluate_portfolio_intelligence_engine",
    "evaluate_portfolio_opportunities",
    "evaluate_portfolio_recommendations",
    "evaluate_portfolio_scenario",
    "portfolio_intelligence_engine_health",
]

PORTFOLIO_INTELLIGENCE_ENGINE_SERVICE_VERSION = "1.0.0"

#: Safety cap on how many unique holdings are analysed per request. This is
#: a latency guard, not a data-honesty concern — holdings beyond this count
#: are reported (not silently dropped) in ``limitations``.
_DEFAULT_MAX_HOLDINGS = 100


def _raw_holdings(portfolio: Mapping[str, Any] | None) -> tuple[Mapping[str, Any], ...]:
    if not portfolio:
        return ()
    holdings = portfolio.get("holdings")
    if not isinstance(holdings, (list, tuple)):
        return ()
    return tuple(h for h in holdings if isinstance(h, Mapping))


def _norm_symbol(row: Mapping[str, Any]) -> str | None:
    symbol = row.get("symbol") or row.get("ticker")
    return str(symbol).strip().upper() if symbol else None


def _confidence_value(raw: Any) -> float | None:
    """Coerce a confidence field that may be a float or ``{value, basis}``."""
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, Mapping) and isinstance(raw.get("value"), (int, float)):
        return float(raw["value"])
    return None


def _numeric_field(
    doc: Mapping[str, Any] | None, section: str, *keys: str
) -> float | None:
    value = extract_field(doc, section, *keys)
    if value == UNAVAILABLE_MESSAGE or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _build_holding_signals(
    raw_holdings: Sequence[Mapping[str, Any]],
    *,
    research: dict[str, ResearchBundle],
    risk_rows_by_symbol: dict[str, Mapping[str, Any]],
) -> tuple[pie.HoldingSignal, ...]:
    signals: list[pie.HoldingSignal] = []
    for row in raw_holdings:
        symbol = _norm_symbol(row)
        weight = row.get("weight")
        if not symbol or weight is None:
            continue
        bundle = research.get(symbol)
        research_linked = bool(
            bundle
            and (
                bundle.research_object is not None
                or bundle.report is not None
                or bundle.snapshot is not None
            )
        )
        doc = (bundle.research_object or bundle.report) if bundle else None

        margin_of_safety = _numeric_field(doc, "margin_of_safety", "margin_of_safety")
        if margin_of_safety is None:
            margin_of_safety = _numeric_field(doc, "recommendation", "margin_of_safety")

        raw_confidence = (
            extract_field(doc, "recommendation", "confidence")
            if doc
            else UNAVAILABLE_MESSAGE
        )
        valuation_confidence = (
            _confidence_value(raw_confidence)
            if raw_confidence != UNAVAILABLE_MESSAGE
            else None
        )

        quality_available = section_available(doc, "business_quality") if doc else False
        quality_score = (
            _numeric_field(doc, "business_quality", "score")
            if quality_available
            else None
        )

        risk_row = risk_rows_by_symbol.get(symbol)

        signals.append(
            pie.HoldingSignal(
                symbol=symbol,
                weight=float(weight),
                sector=row.get("sector") or None,
                country=row.get("country") or None,
                industry=row.get("industry") or None,
                style=row.get("style") or None,
                market_cap_bucket=row.get("market_cap_bucket") or None,
                margin_of_safety=margin_of_safety,
                valuation_confidence=valuation_confidence,
                quality_score=quality_score,
                quality_available=quality_available,
                committee_confidence=valuation_confidence,
                volatility=(
                    float(risk_row["volatility"])
                    if risk_row and isinstance(risk_row.get("volatility"), (int, float))
                    else None
                ),
                risk_contribution_pct=(
                    float(risk_row["risk_contribution_pct"])
                    if risk_row
                    and isinstance(risk_row.get("risk_contribution_pct"), (int, float))
                    else None
                ),
                research_linked=research_linked,
            )
        )
    return tuple(signals)


class _Context:
    """Everything computed once per request — shared by every public function."""

    def __init__(
        self,
        *,
        holdings: tuple[pie.HoldingSignal, ...],
        performance: dict[str, Any] | None,
        risk_attribution: dict[str, Any] | None,
        monte_carlo: dict[str, Any] | None,
        stress_tests: list[dict[str, Any]] | None,
        correlation_matrix: dict[str, Any] | None,
        cash_weight: float | None,
        limitations: tuple[str, ...],
        truncated_symbol_count: int,
    ) -> None:
        self.holdings = holdings
        self.performance = performance
        self.risk_attribution = risk_attribution
        self.monte_carlo = monte_carlo
        self.stress_tests = stress_tests
        self.correlation_matrix = correlation_matrix
        self.cash_weight = cash_weight
        self.limitations = limitations
        self.truncated_symbol_count = truncated_symbol_count


def _build_context(
    portfolio: Mapping[str, Any] | None,
    *,
    research_objects: Mapping[str, Any] | list[Any] | None,
    reports: Mapping[str, Any] | list[Any] | None,
    snapshots: Mapping[str, Any] | list[Any] | None,
    snapshot_ids: Mapping[str, str] | None,
    benchmark_symbol: str | None,
    window_days: int,
    cash_weight: float | None,
    stress_window_ids: Sequence[str] | None,
    as_of: date | str | None,
    max_holdings: int,
) -> _Context:
    raw_holdings = _raw_holdings(portfolio)
    limitations: list[str] = []
    truncated = 0
    if len(raw_holdings) > max_holdings:
        truncated = len(raw_holdings) - max_holdings
        raw_holdings = raw_holdings[:max_holdings]
        limitations.append(
            f"Portfolio has more than {max_holdings} holdings; only the first "
            f"{max_holdings} were analysed ({truncated} holdings excluded) — "
            "latency guard, not a data-availability limitation."
        )

    if not raw_holdings:
        return _Context(
            holdings=(),
            performance=None,
            risk_attribution=None,
            monte_carlo=None,
            stress_tests=None,
            correlation_matrix=None,
            cash_weight=cash_weight,
            limitations=("Data unavailable. No portfolio holdings supplied.",),
            truncated_symbol_count=0,
        )

    trimmed_portfolio = {**(portfolio or {}), "holdings": list(raw_holdings)}

    research = link_research_map(
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
    )

    performance_result = evaluate_portfolio_performance(
        trimmed_portfolio,
        benchmark_symbol=benchmark_symbol,
        window_days=window_days,
        as_of=as_of,
    )
    performance = (
        performance_result.get("result")
        if performance_result.get("available")
        else None
    )
    if not performance_result.get("available"):
        limitations.append(
            "Data unavailable. Portfolio performance ratios could not be "
            "computed (no overlapping authenticated price history)."
        )

    risk_result = evaluate_portfolio_risk_analytics(
        trimmed_portfolio, window_days=window_days, as_of=as_of
    )
    risk_attribution = (
        risk_result.get("risk_attribution") if risk_result.get("available") else None
    )
    correlation_matrix = (
        (risk_attribution or {}).get("correlation_matrix") if risk_attribution else None
    )
    risk_rows_by_symbol: dict[str, Mapping[str, Any]] = {}
    if risk_attribution:
        for row in risk_attribution.get("rows") or ():
            symbol = row.get("symbol")
            if symbol:
                risk_rows_by_symbol[str(symbol)] = row
    else:
        limitations.append(
            "Data unavailable. Risk attribution could not be computed — "
            "per-holding volatility/risk contribution excluded."
        )

    simulation_result = evaluate_portfolio_simulation(
        trimmed_portfolio, window_days=window_days, as_of=as_of
    )
    monte_carlo = (
        simulation_result.get("monte_carlo")
        if simulation_result.get("available")
        else None
    )

    stress_result = evaluate_portfolio_stress_analytics(
        trimmed_portfolio,
        stress_window_ids=stress_window_ids,
        benchmark_symbol=benchmark_symbol,
        window_days=window_days,
        as_of=as_of,
    )
    stress_tests = (
        stress_result.get("stress_tests") if stress_result.get("available") else None
    )

    holdings = _build_holding_signals(
        raw_holdings, research=research, risk_rows_by_symbol=risk_rows_by_symbol
    )

    return _Context(
        holdings=holdings,
        performance=performance,
        risk_attribution=risk_attribution,
        monte_carlo=monte_carlo,
        stress_tests=stress_tests,
        correlation_matrix=correlation_matrix,
        cash_weight=cash_weight,
        limitations=tuple(limitations),
        truncated_symbol_count=truncated,
    )


def evaluate_portfolio_intelligence_engine(
    portfolio: Mapping[str, Any] | None,
    *,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    snapshot_ids: Mapping[str, str] | None = None,
    benchmark_symbol: str | None = None,
    window_days: int = 252,
    cash_weight: float | None = None,
    stress_window_ids: Sequence[str] | None = None,
    as_of: date | str | None = None,
    max_holdings: int = _DEFAULT_MAX_HOLDINGS,
) -> dict[str, Any]:
    """Full Portfolio Intelligence Engine result — every capability at once."""
    ctx = _build_context(
        portfolio,
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
        benchmark_symbol=benchmark_symbol,
        window_days=window_days,
        cash_weight=cash_weight,
        stress_window_ids=stress_window_ids,
        as_of=as_of,
        max_holdings=max_holdings,
    )

    if not ctx.holdings:
        return {
            "available": False,
            "message": "Data unavailable.",
            "limitations": list(ctx.limitations),
        }

    diversification = pie.compute_diversification_score(
        ctx.holdings, correlation_matrix=ctx.correlation_matrix
    )
    concentration = pie.compute_concentration_analysis(ctx.holdings)
    health = pie.compute_health_score(
        ctx.holdings,
        performance=ctx.performance,
        diversification=diversification,
        concentration=concentration,
        cash_weight=ctx.cash_weight,
    )
    valuation_heatmap = pie.compute_valuation_heatmap(ctx.holdings)
    risk_summary = pie.build_risk_summary(
        ctx.holdings,
        performance=ctx.performance,
        monte_carlo=ctx.monte_carlo,
        stress_tests=ctx.stress_tests,
    )
    recommendations = pie.generate_recommendations(ctx.holdings)
    drift = pie.compute_drift_analysis(ctx.holdings)
    opportunities = pie.rank_opportunities(ctx.holdings)
    scenario = pie.build_scenario_summary(ctx.holdings, performance=ctx.performance)

    return {
        "available": True,
        "message": None,
        "service_version": PORTFOLIO_INTELLIGENCE_ENGINE_SERVICE_VERSION,
        "holding_count": len(ctx.holdings),
        "health_score": health.to_public_dict(),
        "concentration": concentration.to_public_dict(),
        "valuation_heatmap": valuation_heatmap.to_public_dict(),
        "risk_summary": risk_summary.to_public_dict(),
        "recommendations": [r.to_public_dict() for r in recommendations],
        "drift": drift.to_public_dict(),
        "diversification": diversification.to_public_dict(),
        "opportunities": opportunities.to_public_dict(),
        "scenario": scenario.to_public_dict(),
        "limitations": list(ctx.limitations),
    }


def evaluate_portfolio_health(
    portfolio: Mapping[str, Any] | None,
    *,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    snapshot_ids: Mapping[str, str] | None = None,
    benchmark_symbol: str | None = None,
    window_days: int = 252,
    cash_weight: float | None = None,
    as_of: date | str | None = None,
    max_holdings: int = _DEFAULT_MAX_HOLDINGS,
) -> dict[str, Any]:
    """Portfolio Health Score only — combines Diversification/Risk/Valuation/
    Quality/Concentration/Cash."""
    ctx = _build_context(
        portfolio,
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
        benchmark_symbol=benchmark_symbol,
        window_days=window_days,
        cash_weight=cash_weight,
        stress_window_ids=None,
        as_of=as_of,
        max_holdings=max_holdings,
    )
    if not ctx.holdings:
        return {
            "available": False,
            "message": "Data unavailable.",
            "limitations": list(ctx.limitations),
        }

    diversification = pie.compute_diversification_score(
        ctx.holdings, correlation_matrix=ctx.correlation_matrix
    )
    concentration = pie.compute_concentration_analysis(ctx.holdings)
    health = pie.compute_health_score(
        ctx.holdings,
        performance=ctx.performance,
        diversification=diversification,
        concentration=concentration,
        cash_weight=ctx.cash_weight,
    )
    return {
        "available": True,
        "message": None,
        "health_score": health.to_public_dict(),
        "diversification": diversification.to_public_dict(),
        "concentration": concentration.to_public_dict(),
        "limitations": list(ctx.limitations),
    }


def evaluate_portfolio_recommendations(
    portfolio: Mapping[str, Any] | None,
    *,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    snapshot_ids: Mapping[str, str] | None = None,
    benchmark_symbol: str | None = None,
    window_days: int = 252,
    as_of: date | str | None = None,
    max_holdings: int = _DEFAULT_MAX_HOLDINGS,
) -> dict[str, Any]:
    """AI Recommendations only — rule-based combination of existing signals."""
    ctx = _build_context(
        portfolio,
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
        benchmark_symbol=benchmark_symbol,
        window_days=window_days,
        cash_weight=None,
        stress_window_ids=None,
        as_of=as_of,
        max_holdings=max_holdings,
    )
    if not ctx.holdings:
        return {
            "available": False,
            "message": "Data unavailable.",
            "limitations": list(ctx.limitations),
        }

    recommendations = pie.generate_recommendations(ctx.holdings)
    return {
        "available": True,
        "message": None,
        "recommendations": [r.to_public_dict() for r in recommendations],
        "limitations": list(ctx.limitations),
    }


def evaluate_portfolio_opportunities(
    portfolio: Mapping[str, Any] | None,
    *,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    snapshot_ids: Mapping[str, str] | None = None,
    benchmark_symbol: str | None = None,
    window_days: int = 252,
    as_of: date | str | None = None,
    max_holdings: int = _DEFAULT_MAX_HOLDINGS,
) -> dict[str, Any]:
    """Portfolio Opportunity Finder only — ranking of existing signals."""
    ctx = _build_context(
        portfolio,
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
        benchmark_symbol=benchmark_symbol,
        window_days=window_days,
        cash_weight=None,
        stress_window_ids=None,
        as_of=as_of,
        max_holdings=max_holdings,
    )
    if not ctx.holdings:
        return {
            "available": False,
            "message": "Data unavailable.",
            "limitations": list(ctx.limitations),
        }

    opportunities = pie.rank_opportunities(ctx.holdings)
    return {
        "available": True,
        "message": None,
        "opportunities": opportunities.to_public_dict(),
        "limitations": list(ctx.limitations),
    }


def evaluate_portfolio_scenario(
    portfolio: Mapping[str, Any] | None,
    *,
    research_objects: Mapping[str, Any] | list[Any] | None = None,
    reports: Mapping[str, Any] | list[Any] | None = None,
    snapshots: Mapping[str, Any] | list[Any] | None = None,
    snapshot_ids: Mapping[str, str] | None = None,
    benchmark_symbol: str | None = None,
    window_days: int = 252,
    as_of: date | str | None = None,
    max_holdings: int = _DEFAULT_MAX_HOLDINGS,
) -> dict[str, Any]:
    """Portfolio AI Committee / Scenario Summary only — Bull/Base/Bear synthesis."""
    ctx = _build_context(
        portfolio,
        research_objects=research_objects,
        reports=reports,
        snapshots=snapshots,
        snapshot_ids=snapshot_ids,
        benchmark_symbol=benchmark_symbol,
        window_days=window_days,
        cash_weight=None,
        stress_window_ids=None,
        as_of=as_of,
        max_holdings=max_holdings,
    )
    if not ctx.holdings:
        return {
            "available": False,
            "message": "Data unavailable.",
            "limitations": list(ctx.limitations),
        }

    scenario = pie.build_scenario_summary(ctx.holdings, performance=ctx.performance)
    return {
        "available": True,
        "message": None,
        "scenario": scenario.to_public_dict(),
        "limitations": list(ctx.limitations),
    }


def portfolio_intelligence_engine_health() -> dict[str, Any]:
    from dsp_platform.portfolio_analytics import portfolio_analytics_health

    return {
        "service_version": PORTFOLIO_INTELLIGENCE_ENGINE_SERVICE_VERSION,
        "engine_package_version": pie.__version__,
        "portfolio_analytics": portfolio_analytics_health(),
    }
