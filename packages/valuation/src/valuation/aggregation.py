"""Aggregate independent method estimates into a valuation assessment core.

Deterministic rules (no forecasting):

* Mid estimate = median of applicable intrinsic values
* Range = (min, median, max)
* Confidence scales with number of applicable methods
* Margin of safety = (mid − market_cap) / mid when market_cap provided

Margin of Safety is a shared-kernel contracts type, computed once here.
"""

from __future__ import annotations

from collections.abc import Sequence

from contracts.domain.margin_of_safety import MarginOfSafety
from valuation.enums import ValuationConfidence
from valuation.methods._math import median_or_none
from valuation.models import (
    IntrinsicValueEstimate,
    MarketSnapshot,
    ValuationEvidence,
    ValuationRange,
)

__all__ = ["aggregate_estimates", "confidence_from_count"]


def confidence_from_count(applicable_count: int) -> ValuationConfidence:
    """Map breadth of applicable methods onto a confidence label."""
    if applicable_count >= 4:
        return ValuationConfidence.HIGH
    if applicable_count >= 2:
        return ValuationConfidence.MEDIUM
    if applicable_count == 1:
        return ValuationConfidence.LOW
    return ValuationConfidence.INSUFFICIENT


def aggregate_estimates(
    estimates: Sequence[IntrinsicValueEstimate],
    market: MarketSnapshot | None = None,
) -> tuple[
    ValuationRange,
    MarginOfSafety,
    ValuationConfidence,
    tuple[ValuationEvidence, ...],
    str,
]:
    """Collapse method estimates into range, MoS, confidence, evidence, reasoning.

    Args:
        estimates: All method results (including non-applicable).
        market: Optional market context for margin of safety.

    Returns:
        ``(range, margin_of_safety, confidence, method_evidence, reasoning)``.

    Raises:
        ValueError: If ``estimates`` is empty.
    """
    if not estimates:
        msg = "estimates must not be empty"
        raise ValueError(msg)

    applicable = [e for e in estimates if e.applicable and e.intrinsic_value is not None]
    values = [float(e.intrinsic_value) for e in applicable]  # type: ignore[arg-type]
    mid = median_or_none(values)
    low = min(values) if values else None
    high = max(values) if values else None
    valuation_range = ValuationRange(low=low, mid=mid, high=high)
    confidence = confidence_from_count(len(applicable))

    market_cap = market.market_cap if market is not None else None
    if mid is not None and mid != 0 and market_cap is not None:
        ratio = (mid - float(market_cap)) / mid
        margin = MarginOfSafety(
            ratio=ratio,
            intrinsic_value=mid,
            market_value=float(market_cap),
            available=True,
        )
    else:
        margin = MarginOfSafety(
            ratio=None,
            intrinsic_value=mid,
            market_value=market_cap,
            available=False,
        )

    evidence = tuple(
        ValuationEvidence(
            method=e.method,
            claim=e.rationale,
            value=e.intrinsic_value,
            reference=e.formula,
        )
        for e in estimates
    )

    skipped = [e.method.value for e in estimates if not e.applicable]
    if applicable:
        methods = ", ".join(e.method.value for e in applicable)
        reasoning = (
            f"{len(applicable)} applicable method(s) [{methods}] "
            f"yield range low={_fmt(low)}, mid={_fmt(mid)}, high={_fmt(high)}; "
            f"confidence={confidence.value}."
        )
        if skipped:
            reasoning += f" Skipped: {', '.join(skipped)}."
        if margin.available and margin.ratio is not None:
            reasoning += f" Margin of safety={margin.ratio:.2%}."
        else:
            reasoning += " Margin of safety unavailable."
    else:
        reasoning = (
            "No valuation methods were applicable given available inputs; "
            f"confidence={confidence.value}."
        )
        if skipped:
            reasoning += f" Skipped: {', '.join(skipped)}."

    return valuation_range, margin, confidence, evidence, reasoning


def _fmt(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.2f}"
