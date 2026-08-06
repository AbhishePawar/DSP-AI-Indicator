"""Sector & Style Drift — deviation from an even-split reference baseline.

Sector drift compares caller-supplied sector weights against the published
11-sector GICS taxonomy (an even 1/11 baseline — the simplest, most
transparent reference that requires no invented "target portfolio" or
external index composition). Style/cap drift requires the caller to supply
``style``/``market_cap_bucket`` per holding; when absent, the corresponding
drift dimension is honestly reported unavailable.
"""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_intelligence_engine.enums import DriftDirection, IntelligenceStatus
from portfolio_intelligence_engine.models import DriftAnalysis, DriftRow, HoldingSignal
from portfolio_intelligence_engine.reference import (
    CAP_BUCKETS,
    DRIFT_BAND_PCT,
    GICS_SECTORS,
    STYLE_BUCKETS,
)

__all__ = ["compute_drift_analysis"]


def _direction(weight: float, baseline: float) -> DriftDirection:
    if weight <= 0.0:
        return DriftDirection.MISSING
    if weight >= baseline * (1 + DRIFT_BAND_PCT):
        return DriftDirection.OVERWEIGHT
    if weight <= baseline * (1 - DRIFT_BAND_PCT):
        return DriftDirection.UNDERWEIGHT
    return DriftDirection.IN_LINE


def _bucket_drift(
    holdings: Sequence[HoldingSignal], *, attr: str, universe: Sequence[str]
) -> tuple[tuple[DriftRow, ...], tuple[str, ...], float]:
    total_weight = sum(h.weight for h in holdings) or 1.0
    weights: dict[str, float] = {}
    unclassified = 0.0
    for h in holdings:
        label = getattr(h, attr)
        if not label:
            unclassified += h.weight
            continue
        weights[label] = weights.get(label, 0.0) + h.weight / total_weight
    baseline = 1.0 / len(universe)
    rows = tuple(
        DriftRow(
            label=label,
            weight=weights.get(label, 0.0),
            baseline_weight=baseline,
            direction=_direction(weights.get(label, 0.0), baseline),
        )
        for label in universe
    )
    missing = tuple(
        row.label for row in rows if row.direction is DriftDirection.MISSING
    )
    return rows, missing, unclassified


def compute_drift_analysis(holdings: Sequence[HoldingSignal]) -> DriftAnalysis:
    if not holdings:
        return DriftAnalysis(
            status=IntelligenceStatus.UNAVAILABLE,
            sector_drift=(),
            missing_sectors=(),
            style_drift=(),
            cap_drift=(),
            limitations=("no portfolio holdings supplied.",),
        )

    sector_rows, missing_sectors, sector_unclassified = _bucket_drift(
        holdings, attr="sector", universe=GICS_SECTORS
    )

    limitations: list[str] = []
    if sector_unclassified > 0:
        limitations.append(
            f"{sector_unclassified:.1%} of portfolio weight has no resolvable "
            "sector and is excluded from sector drift."
        )

    style_rows: tuple[DriftRow, ...] = ()
    if any(h.style for h in holdings):
        style_rows, _, style_unclassified = _bucket_drift(
            holdings, attr="style", universe=STYLE_BUCKETS
        )
        if style_unclassified > 0:
            limitations.append(
                f"{style_unclassified:.1%} of portfolio weight has no caller-supplied "
                "style label and is excluded from style drift."
            )
    else:
        limitations.append(
            "Data unavailable. No caller-supplied style (growth/value/blend) labels — "
            "style drift not computed."
        )

    cap_rows: tuple[DriftRow, ...] = ()
    if any(h.market_cap_bucket for h in holdings):
        cap_rows, _, cap_unclassified = _bucket_drift(
            holdings, attr="market_cap_bucket", universe=CAP_BUCKETS
        )
        if cap_unclassified > 0:
            limitations.append(
                f"{cap_unclassified:.1%} of portfolio weight has no caller-supplied "
                "market-cap bucket and is excluded from cap-size drift."
            )
    else:
        limitations.append(
            "Data unavailable. No caller-supplied market-cap bucket "
            "(large/mid/small) labels — cap-size drift not computed."
        )

    status = (
        IntelligenceStatus.COMPLETE
        if style_rows and cap_rows and not limitations
        else IntelligenceStatus.PARTIAL
    )

    return DriftAnalysis(
        status=status,
        sector_drift=sector_rows,
        missing_sectors=missing_sectors,
        style_drift=style_rows,
        cap_drift=cap_rows,
        limitations=tuple(limitations),
    )
