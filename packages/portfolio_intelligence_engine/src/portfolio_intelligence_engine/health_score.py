"""Portfolio Health Score (0-100) — a disclosed weighted composite only.

Every sub-score is derived from a number already produced elsewhere
(``portfolio_analytics`` for risk, the Diversification Score/Concentration
Analysis modules in this package which themselves only combine existing
signals, and caller-linked valuation/quality via EPIC-A002 pass-through).
This module performs no valuation, risk, or quality computation of its own —
it only maps already-computed metrics onto a common 0-100 scale and
combines them with disclosed, documented weights. Any sub-score whose input
is missing is marked ``available=False`` and excluded from the composite;
the remaining weights are renormalized — never fabricated.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from portfolio_intelligence_engine.enums import IntelligenceStatus
from portfolio_intelligence_engine.models import (
    ConcentrationAnalysis,
    DiversificationScore,
    HealthScoreResult,
    HealthSubScore,
    HoldingSignal,
)

__all__ = ["compute_health_score"]

#: Disclosed default weights (sum to 1.0). Every one is documented in
#: docs/PORTFOLIO_GUIDE.md and may be overridden by the caller.
_DEFAULT_WEIGHTS: dict[str, float] = {
    "diversification": 0.20,
    "risk": 0.20,
    "valuation": 0.20,
    "quality": 0.20,
    "concentration": 0.15,
    "cash_allocation": 0.05,
}

_IDEAL_CASH_MIN = 0.02
_IDEAL_CASH_MAX = 0.15


def _clamp(value: float, *, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _risk_sub_score(
    performance: Mapping[str, object] | None,
) -> tuple[float | None, str]:
    if performance is None:
        return None, "Data unavailable. No performance ratios supplied."
    volatility = performance.get("annualized_volatility")
    max_dd = performance.get("max_drawdown")
    if not isinstance(volatility, (int, float)) and not isinstance(
        max_dd, (int, float)
    ):
        return None, "Data unavailable. No volatility/max-drawdown supplied."
    penalty = 0.0
    parts: list[str] = []
    if isinstance(volatility, (int, float)):
        penalty += float(volatility) * 200.0
        parts.append(f"annualized volatility {volatility:.1%}")
    if isinstance(max_dd, (int, float)):
        penalty += abs(float(max_dd)) * 100.0
        parts.append(f"max drawdown {max_dd:.1%}")
    score = _clamp(100.0 - penalty)
    return score, "Derived from " + " and ".join(
        parts
    ) + " (portfolio_analytics, reused)."


def _valuation_sub_score(holdings: Sequence[HoldingSignal]) -> tuple[float | None, str]:
    weighted = [
        (h.weight, h.margin_of_safety)
        for h in holdings
        if h.margin_of_safety is not None
    ]
    if not weighted:
        return None, "Data unavailable. No holdings have a linked margin of safety."
    total_weight = sum(w for w, _ in weighted)
    avg_mos = (
        sum(w * mos for w, mos in weighted) / total_weight if total_weight else None
    )
    if avg_mos is None:
        return None, "Data unavailable. No holdings have a linked margin of safety."
    score = _clamp(50.0 + avg_mos * 100.0)
    coverage = total_weight / (sum(h.weight for h in holdings) or 1.0)
    return score, (
        f"Weighted-average margin of safety of {avg_mos:.1%} across {coverage:.0%} "
        "of portfolio weight (Valuation Engine, linked Research Objects)."
    )


def _quality_sub_score(holdings: Sequence[HoldingSignal]) -> tuple[float | None, str]:
    weighted = [
        (h.weight, h.quality_score) for h in holdings if h.quality_score is not None
    ]
    if not weighted:
        return (
            None,
            "Data unavailable. No holdings have a linked business-quality score.",
        )
    total_weight = sum(w for w, _ in weighted)
    avg_quality = (
        sum(w * q for w, q in weighted) / total_weight if total_weight else None
    )
    if avg_quality is None:
        return (
            None,
            "Data unavailable. No holdings have a linked business-quality score.",
        )
    coverage = total_weight / (sum(h.weight for h in holdings) or 1.0)
    return _clamp(avg_quality), (
        f"Weighted-average business-quality score across {coverage:.0%} of "
        "portfolio weight (composition pipeline stage summaries, reused)."
    )


def _concentration_sub_score(
    concentration: ConcentrationAnalysis,
) -> tuple[float | None, str]:
    if concentration.herfindahl_index is None:
        return None, "Data unavailable. No concentration analysis supplied."
    score = _clamp((1.0 - concentration.herfindahl_index) * 100.0)
    hhi = concentration.herfindahl_index
    return score, f"Derived from a position Herfindahl index of {hhi:.3f}."


def _cash_sub_score(cash_weight: float | None) -> tuple[float | None, str]:
    if cash_weight is None:
        return None, "Data unavailable. No caller-declared cash weight supplied."
    if _IDEAL_CASH_MIN <= cash_weight <= _IDEAL_CASH_MAX:
        return 100.0, f"Cash allocation of {cash_weight:.1%} is within the 2%-15% band."
    distance = min(
        abs(cash_weight - _IDEAL_CASH_MIN), abs(cash_weight - _IDEAL_CASH_MAX)
    )
    score = _clamp(100.0 - distance * 400.0)
    return score, (
        f"Cash allocation of {cash_weight:.1%} is outside the disclosed 2%-15% band."
    )


def compute_health_score(
    holdings: Sequence[HoldingSignal],
    *,
    performance: Mapping[str, object] | None,
    diversification: DiversificationScore,
    concentration: ConcentrationAnalysis,
    cash_weight: float | None = None,
    weights: Mapping[str, float] | None = None,
) -> HealthScoreResult:
    if not holdings:
        return HealthScoreResult(
            status=IntelligenceStatus.UNAVAILABLE,
            score=None,
            components=(),
            limitations=("no portfolio holdings supplied.",),
        )

    w = dict(_DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    div_score, div_explanation = (
        diversification.score,
        (
            "Diversification Score (this package, combining holding count, sector "
            "spread, position sizing, and correlation)."
            if diversification.score is not None
            else "Data unavailable. Diversification Score could not be computed."
        ),
    )
    risk_score, risk_explanation = _risk_sub_score(performance)
    valuation_score, valuation_explanation = _valuation_sub_score(holdings)
    quality_score, quality_explanation = _quality_sub_score(holdings)
    concentration_score, concentration_explanation = _concentration_sub_score(
        concentration
    )
    cash_score, cash_explanation = _cash_sub_score(cash_weight)

    raw_components = {
        "diversification": (div_score, div_explanation),
        "risk": (risk_score, risk_explanation),
        "valuation": (valuation_score, valuation_explanation),
        "quality": (quality_score, quality_explanation),
        "concentration": (concentration_score, concentration_explanation),
        "cash_allocation": (cash_score, cash_explanation),
    }

    available_weight_total = sum(
        w[name] for name, (score, _) in raw_components.items() if score is not None
    )

    components: list[HealthSubScore] = []
    weighted_sum = 0.0
    for name, (score, explanation) in raw_components.items():
        available = score is not None
        contribution = None
        if available and available_weight_total > 0:
            normalized_weight = w[name] / available_weight_total
            contribution = score * normalized_weight
            weighted_sum += contribution
        components.append(
            HealthSubScore(
                name=name,
                available=available,
                score=score,
                weight=w[name],
                contribution=contribution,
                explanation=explanation,
            )
        )

    total_score = weighted_sum if available_weight_total > 0 else None
    limitations = tuple(c.explanation for c in components if not c.available)
    available_count = sum(1 for c in components if c.available)
    status = (
        IntelligenceStatus.UNAVAILABLE
        if available_count == 0
        else (
            IntelligenceStatus.COMPLETE
            if available_count == len(components)
            else IntelligenceStatus.PARTIAL
        )
    )

    return HealthScoreResult(
        status=status,
        score=total_score,
        components=tuple(components),
        limitations=limitations,
    )
