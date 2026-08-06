"""Portfolio Concentration Analysis — aggregation of caller-supplied weights only."""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_intelligence_engine.enums import AllocationKind, IntelligenceStatus
from portfolio_intelligence_engine.models import (
    ConcentrationAnalysis,
    ConcentrationFlag,
    HoldingSignal,
)
from portfolio_intelligence_engine.reference import (
    CONCENTRATION_COUNTRY_FLAG_PCT,
    CONCENTRATION_INDUSTRY_FLAG_PCT,
    CONCENTRATION_SECTOR_FLAG_PCT,
    CONCENTRATION_SINGLE_POSITION_FLAG_PCT,
    CONCENTRATION_STYLE_FLAG_PCT,
)

__all__ = ["compute_concentration_analysis"]


def _bucket_weights(
    holdings: Sequence[HoldingSignal], *, attr: str
) -> tuple[list[dict[str, object]], float]:
    weights: dict[str, float] = {}
    symbols: dict[str, list[str]] = {}
    unclassified = 0.0
    for h in holdings:
        label = getattr(h, attr)
        if not label:
            unclassified += h.weight
            continue
        weights[label] = weights.get(label, 0.0) + h.weight
        symbols.setdefault(label, []).append(h.symbol)
    rows = [
        {"label": label, "weight": weight, "symbols": symbols[label]}
        for label, weight in sorted(weights.items(), key=lambda kv: -kv[1])
    ]
    return rows, unclassified


def compute_concentration_analysis(
    holdings: Sequence[HoldingSignal],
    *,
    top_n: int = 10,
) -> ConcentrationAnalysis:
    """Identify largest holdings and sector/industry/style/country concentration."""
    if not holdings:
        return ConcentrationAnalysis(
            status=IntelligenceStatus.UNAVAILABLE,
            largest_holdings=(),
            sector_concentration=(),
            industry_concentration=(),
            style_concentration=(),
            country_concentration=(),
            herfindahl_index=None,
            flags=(),
            limitations=("no portfolio holdings supplied.",),
        )

    total_weight = sum(h.weight for h in holdings) or 1.0
    ordered = sorted(holdings, key=lambda h: (-h.weight, h.symbol))
    largest = [
        {
            "symbol": h.symbol,
            "weight": h.weight,
            "weight_pct_of_portfolio": h.weight / total_weight,
        }
        for h in ordered[:top_n]
    ]

    sector_rows, sector_unclassified = _bucket_weights(holdings, attr="sector")
    industry_rows, industry_unclassified = _bucket_weights(holdings, attr="industry")
    style_rows, style_unclassified = _bucket_weights(holdings, attr="style")
    country_rows, country_unclassified = _bucket_weights(holdings, attr="country")

    hhi = sum((h.weight / total_weight) ** 2 for h in holdings)

    flags: list[ConcentrationFlag] = []
    for h in holdings:
        if h.weight / total_weight >= CONCENTRATION_SINGLE_POSITION_FLAG_PCT:
            flags.append(
                ConcentrationFlag(
                    kind=AllocationKind.POSITION,
                    label=h.symbol,
                    weight=h.weight / total_weight,
                    threshold=CONCENTRATION_SINGLE_POSITION_FLAG_PCT,
                    symbols=(h.symbol,),
                )
            )
    for row, kind, threshold in (
        (sector_rows, AllocationKind.SECTOR, CONCENTRATION_SECTOR_FLAG_PCT),
        (industry_rows, AllocationKind.INDUSTRY, CONCENTRATION_INDUSTRY_FLAG_PCT),
        (style_rows, AllocationKind.STYLE, CONCENTRATION_STYLE_FLAG_PCT),
        (country_rows, AllocationKind.COUNTRY, CONCENTRATION_COUNTRY_FLAG_PCT),
    ):
        for bucket in row:
            pct = bucket["weight"] / total_weight
            if pct >= threshold:
                flags.append(
                    ConcentrationFlag(
                        kind=kind,
                        label=str(bucket["label"]),
                        weight=pct,
                        threshold=threshold,
                        symbols=tuple(bucket["symbols"]),
                    )
                )

    limitations: list[str] = []
    if industry_unclassified > 0:
        limitations.append(
            "industry concentration excludes holdings without a caller-supplied "
            "industry label — Data unavailable for those positions."
        )
    if style_unclassified > 0:
        limitations.append(
            "style concentration excludes holdings without a caller-supplied "
            "style label (growth/value/blend) — Data unavailable for those positions."
        )
    if country_unclassified > 0:
        limitations.append(
            "country concentration excludes holdings without a resolvable country."
        )
    if sector_unclassified > 0:
        limitations.append(
            "sector concentration excludes holdings without a resolvable sector."
        )

    return ConcentrationAnalysis(
        status=IntelligenceStatus.COMPLETE
        if not limitations
        else IntelligenceStatus.PARTIAL,
        largest_holdings=tuple(largest),
        sector_concentration=tuple(sector_rows),
        industry_concentration=tuple(industry_rows),
        style_concentration=tuple(style_rows),
        country_concentration=tuple(country_rows),
        herfindahl_index=hhi,
        flags=tuple(flags),
        limitations=tuple(limitations),
    )
