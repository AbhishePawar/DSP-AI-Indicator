"""Portfolio Scenario / AI Committee Summary — disclosed aggregation only.

This module never runs a new AI Committee vote and never re-derives a
valuation scenario. It combines numbers that already exist:

- **Base Case** implied return = the portfolio's weighted-average margin of
  safety (Valuation Engine, pass-through via EPIC-A002).
- **Bull/Bear** cases = Base Case ± the portfolio's own trailing annualized
  volatility (``portfolio_analytics``) — a transparent dispersion band, not
  a re-run DCF scenario.
- **Expected CAGR** = the portfolio's trailing realized annualized return
  (``portfolio_analytics.evaluate_portfolio_performance``) — historical, not
  a forecast. Explicitly labelled as such.
- **Worst-case drawdown** = the portfolio's trailing realized max drawdown
  (same engine) — historical, not a stress-test projection.
- **Confidence** = the coverage-weighted average of already-computed
  per-holding valuation/committee confidence, discounted by the fraction of
  holdings that are research-linked at all.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from portfolio_intelligence_engine.enums import IntelligenceStatus
from portfolio_intelligence_engine.models import (
    HoldingSignal,
    PortfolioScenarioSummary,
    ScenarioCase,
)

__all__ = ["build_scenario_summary"]


def build_scenario_summary(
    holdings: Sequence[HoldingSignal],
    *,
    performance: Mapping[str, object] | None,
) -> PortfolioScenarioSummary:
    if not holdings:
        return PortfolioScenarioSummary(
            status=IntelligenceStatus.UNAVAILABLE,
            cases=(),
            expected_cagr=None,
            expected_cagr_basis=None,
            worst_case_drawdown=None,
            worst_case_drawdown_basis=None,
            confidence=None,
            confidence_basis=None,
            limitations=("no portfolio holdings supplied.",),
        )

    total_weight = sum(h.weight for h in holdings) or 1.0
    mos_weighted = [
        (h.weight / total_weight, h.margin_of_safety)
        for h in holdings
        if h.margin_of_safety is not None
    ]
    limitations: list[str] = []

    base_return: float | None = None
    if mos_weighted:
        covered_weight = sum(w for w, _ in mos_weighted)
        base_return = sum(w * mos for w, mos in mos_weighted) / covered_weight
        if covered_weight < 0.999:
            limitations.append(
                f"Base Case covers only {covered_weight:.1%} of portfolio weight "
                "with a linked margin of safety; uncovered weight is excluded, "
                "not assumed fairly valued."
            )
    else:
        limitations.append(
            "Data unavailable. No holdings have a linked margin of safety — "
            "Base/Bull/Bear cases cannot be derived."
        )

    volatility = None
    if performance is not None:
        vol = performance.get("annualized_volatility")
        volatility = float(vol) if isinstance(vol, (int, float)) else None

    cases: tuple[ScenarioCase, ...] = ()
    if base_return is not None:
        band = volatility if volatility is not None else 0.0
        if volatility is None:
            limitations.append(
                "Data unavailable. No portfolio volatility supplied — Bull/Bear "
                "band defaults to the Base Case (zero-width band)."
            )
        cases = (
            ScenarioCase(case="bear", implied_return_pct=base_return - band),
            ScenarioCase(case="base", implied_return_pct=base_return),
            ScenarioCase(case="bull", implied_return_pct=base_return + band),
        )

    expected_cagr = None
    expected_cagr_basis = None
    worst_case_drawdown = None
    worst_case_drawdown_basis = None
    if performance is not None:
        ann_return = performance.get("annualized_return")
        if isinstance(ann_return, (int, float)):
            expected_cagr = float(ann_return)
            expected_cagr_basis = (
                "Trailing realized annualized portfolio return "
                "(portfolio_analytics.evaluate_portfolio_performance) — "
                "historical, not a forecast."
            )
        max_dd = performance.get("max_drawdown")
        if isinstance(max_dd, (int, float)):
            worst_case_drawdown = float(max_dd)
            worst_case_drawdown_basis = (
                "Trailing realized maximum drawdown over the analysis window — "
                "historical, not a stress-test projection. See Stress Testing for "
                "scenario-based downside estimates."
            )
    else:
        limitations.append(
            "Data unavailable. No performance ratios supplied — expected CAGR "
            "and worst-case drawdown cannot be summarized."
        )

    confidences = [
        c
        for c in (
            (
                h.valuation_confidence
                if h.valuation_confidence is not None
                else h.committee_confidence
            )
            for h in holdings
        )
        if c is not None
    ]
    linked_count = sum(1 for h in holdings if h.research_linked)
    coverage = linked_count / len(holdings)
    confidence = None
    confidence_basis = None
    if confidences:
        confidence = (sum(confidences) / len(confidences)) * coverage
        confidence_basis = (
            f"Average of {len(confidences)} linked valuation/committee confidence "
            f"scores, discounted by research-link coverage ({coverage:.0%} of "
            "holdings have a linked Research Object)."
        )
    else:
        limitations.append(
            "Data unavailable. No holdings have a linked valuation/committee "
            "confidence score."
        )

    available_parts = sum(
        1
        for v in (base_return, expected_cagr, worst_case_drawdown, confidence)
        if v is not None
    )
    status = (
        IntelligenceStatus.UNAVAILABLE
        if available_parts == 0
        else (
            IntelligenceStatus.COMPLETE
            if available_parts == 4
            else IntelligenceStatus.PARTIAL
        )
    )

    return PortfolioScenarioSummary(
        status=status,
        cases=cases,
        expected_cagr=expected_cagr,
        expected_cagr_basis=expected_cagr_basis,
        worst_case_drawdown=worst_case_drawdown,
        worst_case_drawdown_basis=worst_case_drawdown_basis,
        confidence=confidence,
        confidence_basis=confidence_basis,
        limitations=tuple(limitations),
    )
