"""Portfolio Risk Summary — aggregation + highlighting of existing Risk
Engine output only.

Every numeric input here (``beta``, ``annualized_volatility``, ``max_drawdown``,
``tracking_error``, Monte Carlo percentiles, stress-test results, per-holding
volatility/risk-contribution) is computed by the frozen
``portfolio_analytics`` engine (RC1 Milestone 1). This module never
recomputes any of them — it only assembles a summary and highlights the
highest-risk holdings by an already-computed risk-contribution ranking.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from portfolio_intelligence_engine.enums import IntelligenceStatus
from portfolio_intelligence_engine.models import (
    HoldingSignal,
    RiskHighlight,
    RiskSummary,
)

__all__ = ["build_risk_summary"]

#: Value at Risk (95%) is not a new calculation — it is the already-computed
#: 5th-percentile terminal return from ``portfolio_analytics.compute_monte_carlo``
#: (bootstrap resampling), relabelled as a loss (sign-flipped when negative).
_VAR_METHOD = (
    "dsp.portfolio_analytics.method.monte_carlo.bootstrap.v1 "
    "(5th percentile terminal return, relabelled as Value at Risk)"
)


def build_risk_summary(
    holdings: Sequence[HoldingSignal],
    *,
    performance: Mapping[str, object] | None,
    monte_carlo: Mapping[str, object] | None,
    stress_tests: Sequence[Mapping[str, object]] | None,
    top_n: int = 5,
) -> RiskSummary:
    limitations: list[str] = []

    beta = _get(performance, "beta")
    volatility = _get(performance, "annualized_volatility")
    max_drawdown = _get(performance, "max_drawdown")
    tracking_error = _get(performance, "tracking_error")
    if performance is None:
        limitations.append(
            "Data unavailable. No performance ratios supplied — beta, volatility, "
            "max drawdown, and tracking error cannot be summarized."
        )

    var_95: float | None = None
    if monte_carlo is not None:
        percentiles = monte_carlo.get("percentiles")
        if isinstance(percentiles, Mapping):
            p5 = percentiles.get("p5")
            if isinstance(p5, (int, float)):
                var_95 = -float(p5) if p5 < 0 else 0.0
    else:
        limitations.append(
            "Data unavailable. No Monte Carlo simulation supplied — Value at Risk "
            "cannot be derived."
        )

    limitations.append(
        "Conditional VaR (Expected Shortfall) is Data unavailable. — the "
        "underlying Monte Carlo engine exposes percentile summaries only, not "
        "the full terminal-return distribution required for an honest tail "
        "average; this package does not approximate it."
    )

    highlights: list[RiskHighlight] = []
    ranked = sorted(
        (h for h in holdings if h.risk_contribution_pct is not None),
        key=lambda h: -(h.risk_contribution_pct or 0.0),
    )
    for h in ranked[:top_n]:
        highlights.append(
            RiskHighlight(
                symbol=h.symbol,
                weight=h.weight,
                volatility=h.volatility,
                risk_contribution_pct=h.risk_contribution_pct,
            )
        )
    if holdings and not ranked:
        limitations.append(
            "Data unavailable. No per-holding risk attribution supplied — "
            "cannot highlight highest-risk holdings."
        )

    stress_count = len([s for s in (stress_tests or ()) if s.get("available")])

    all_unavailable = performance is None and monte_carlo is None and not ranked
    status = (
        IntelligenceStatus.UNAVAILABLE
        if all_unavailable
        else (
            IntelligenceStatus.COMPLETE
            if performance is not None and ranked
            else IntelligenceStatus.PARTIAL
        )
    )

    return RiskSummary(
        status=status,
        beta=beta,
        annualized_volatility=volatility,
        max_drawdown=max_drawdown,
        tracking_error=tracking_error,
        value_at_risk_95=var_95,
        value_at_risk_method=_VAR_METHOD if var_95 is not None else None,
        conditional_value_at_risk_95=None,
        stress_test_count=stress_count,
        monte_carlo_available=monte_carlo is not None,
        highest_risk_holdings=tuple(highlights),
        limitations=tuple(limitations),
    )


def _get(mapping: Mapping[str, object] | None, key: str) -> float | None:
    if mapping is None:
        return None
    value = mapping.get(key)
    return float(value) if isinstance(value, (int, float)) else None
