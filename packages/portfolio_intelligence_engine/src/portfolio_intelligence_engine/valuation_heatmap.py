"""Valuation Heatmap — classification of caller-supplied valuation signals only.

Every ``margin_of_safety``/``confidence`` value consumed here is produced by
the frozen Valuation Engine and surfaced through
``dsp_platform.evaluate_portfolio_intelligence`` (EPIC-A002, linked Research
Objects). This module performs **no valuation math** — it only buckets an
already-computed number against a disclosed threshold.
"""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_intelligence_engine.enums import IntelligenceStatus, ValuationClass
from portfolio_intelligence_engine.models import (
    HoldingSignal,
    ValuationHeatmap,
    ValuationHeatmapRow,
)
from portfolio_intelligence_engine.reference import (
    VALUATION_OVERVALUED_THRESHOLD,
    VALUATION_UNDERVALUED_THRESHOLD,
)

__all__ = ["classify_valuation", "compute_valuation_heatmap"]


def classify_valuation(margin_of_safety: float | None) -> ValuationClass:
    """Classify a holding as Undervalued / Fairly Valued / Overvalued from MoS."""
    if margin_of_safety is None:
        return ValuationClass.UNAVAILABLE
    if margin_of_safety >= VALUATION_UNDERVALUED_THRESHOLD:
        return ValuationClass.UNDERVALUED
    if margin_of_safety <= VALUATION_OVERVALUED_THRESHOLD:
        return ValuationClass.OVERVALUED
    return ValuationClass.FAIRLY_VALUED


def compute_valuation_heatmap(holdings: Sequence[HoldingSignal]) -> ValuationHeatmap:
    """Classify every holding and roll weights up by valuation bucket."""
    if not holdings:
        return ValuationHeatmap(
            status=IntelligenceStatus.UNAVAILABLE,
            rows=(),
            undervalued_weight=0.0,
            fairly_valued_weight=0.0,
            overvalued_weight=0.0,
            unavailable_weight=0.0,
            limitations=("no portfolio holdings supplied.",),
        )

    rows: list[ValuationHeatmapRow] = []
    weights_by_class = dict.fromkeys(ValuationClass, 0.0)
    unavailable_count = 0
    for h in holdings:
        klass = classify_valuation(h.margin_of_safety)
        weights_by_class[klass] += h.weight
        message = None
        if klass is ValuationClass.UNAVAILABLE:
            unavailable_count += 1
            message = (
                "Data unavailable. No linked valuation (margin of safety) for "
                f"{h.symbol} — link a Research Object to enable this row."
            )
        rows.append(
            ValuationHeatmapRow(
                symbol=h.symbol,
                weight=h.weight,
                valuation_class=klass,
                margin_of_safety=h.margin_of_safety,
                confidence=h.valuation_confidence,
                message=message,
            )
        )

    limitations: list[str] = []
    if unavailable_count:
        limitations.append(
            f"{unavailable_count} of {len(holdings)} holdings have no linked "
            "valuation — see per-row messages."
        )

    return ValuationHeatmap(
        status=(
            IntelligenceStatus.UNAVAILABLE
            if unavailable_count == len(holdings)
            else (
                IntelligenceStatus.PARTIAL
                if unavailable_count
                else IntelligenceStatus.COMPLETE
            )
        ),
        rows=tuple(rows),
        undervalued_weight=weights_by_class[ValuationClass.UNDERVALUED],
        fairly_valued_weight=weights_by_class[ValuationClass.FAIRLY_VALUED],
        overvalued_weight=weights_by_class[ValuationClass.OVERVALUED],
        unavailable_weight=weights_by_class[ValuationClass.UNAVAILABLE],
        limitations=tuple(limitations),
    )
