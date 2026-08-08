"""Portfolio summary builders (EPIC-A002) — aggregate existing research only."""

from __future__ import annotations

from typing import Any

from dsp_platform.portfolio_intelligence.linker import (
    ResearchBundle,
    extract_field,
    section_available,
)
from dsp_platform.portfolio_intelligence.models import (
    UNAVAILABLE_MESSAGE,
    Holding,
    LinkedHolding,
    Portfolio,
    Watchlist,
)

__all__ = [
    "build_linked_holdings",
    "build_summaries",
]


def build_linked_holdings(
    holdings: tuple[Holding, ...],
    research: dict[str, ResearchBundle],
) -> tuple[LinkedHolding, ...]:
    linked: list[LinkedHolding] = []
    for holding in holdings:
        bundle = research.get(holding.symbol)
        if bundle is None or (
            bundle.research_object is None
            and bundle.report is None
            and bundle.snapshot is None
        ):
            linked.append(
                LinkedHolding(
                    symbol=holding.symbol,
                    weight=holding.weight,
                    research_linked=False,
                    research_object_id=None,
                    report_id=None,
                    snapshot_id=None,
                    sector=UNAVAILABLE_MESSAGE,
                    industry=UNAVAILABLE_MESSAGE,
                    margin_of_safety=UNAVAILABLE_MESSAGE,
                    business_quality_available=False,
                    risk_available=False,
                    recommendation_available=False,
                    message=UNAVAILABLE_MESSAGE,
                )
            )
            continue
        doc = bundle.research_object or bundle.report
        sector = extract_field(doc, "identity", "sector")
        if sector == UNAVAILABLE_MESSAGE:
            sector = extract_field(doc, "executive_summary", "sector")
        industry = extract_field(doc, "identity", "industry")
        mos = extract_field(
            doc, "margin_of_safety", "margin_of_safety"
        )
        if mos == UNAVAILABLE_MESSAGE:
            mos = extract_field(doc, "recommendation", "margin_of_safety")
        linked.append(
            LinkedHolding(
                symbol=holding.symbol,
                weight=holding.weight,
                research_linked=True,
                research_object_id=bundle.research_object_id,
                report_id=bundle.report_id,
                snapshot_id=bundle.snapshot_id,
                sector=sector,
                industry=industry,
                margin_of_safety=mos,
                business_quality_available=section_available(doc, "business_quality"),
                risk_available=section_available(doc, "risk"),
                recommendation_available=section_available(doc, "recommendation"),
                message=None,
            )
        )
    return tuple(linked)


def build_summaries(
    *,
    portfolio: Portfolio | None,
    watchlist: Watchlist | None,
    linked: tuple[LinkedHolding, ...],
    research: dict[str, ResearchBundle],
) -> dict[str, Any]:
    holdings = portfolio.holdings if portfolio else ()
    linked_count = sum(1 for h in linked if h.research_linked)
    missing = [
        {
            "symbol": h.symbol,
            "weight": h.weight,
            "message": UNAVAILABLE_MESSAGE,
        }
        for h in linked
        if not h.research_linked
    ]

    # Sector allocation: sum user-provided weights by sector label from research
    sector_weights: dict[str, float] = {}
    sector_unknown_weight = 0.0
    for h in linked:
        if h.weight is None:
            continue
        sector = h.sector
        if sector == UNAVAILABLE_MESSAGE or sector is None:
            sector_unknown_weight += float(h.weight)
        else:
            key = str(sector)
            sector_weights[key] = sector_weights.get(key, 0.0) + float(h.weight)

    sectors_sorted = [
        {"sector": k, "weight_sum": sector_weights[k]}
        for k in sorted(sector_weights.keys())
    ]
    if sector_unknown_weight:
        sectors_sorted.append(
            {"sector": UNAVAILABLE_MESSAGE, "weight_sum": sector_unknown_weight}
        )

    # Concentration: holdings ordered by provided weight (desc), no optimisation
    with_weight = [h for h in linked if h.weight is not None]
    with_weight_sorted = sorted(
        with_weight, key=lambda h: (-float(h.weight or 0.0), h.symbol)
    )
    top = [
        {"symbol": h.symbol, "weight": h.weight, "research_linked": h.research_linked}
        for h in with_weight_sorted[:5]
    ]

    # MoS / quality / risk: pass-through lists from linked research (no new scores)
    mos_rows = [
        {
            "symbol": h.symbol,
            "margin_of_safety": h.margin_of_safety,
            "research_object_id": h.research_object_id,
        }
        for h in linked
    ]
    quality_rows = []
    risk_rows = []
    for h in linked:
        bundle = research.get(h.symbol)
        doc = bundle.research_object or bundle.report if bundle else None
        quality_rows.append(
            {
                "symbol": h.symbol,
                "available": h.business_quality_available,
                "payload": (
                    (doc or {}).get("business_quality", {}).get("payload")
                    if h.business_quality_available and isinstance(doc, dict)
                    else None
                ),
                "message": None if h.business_quality_available else UNAVAILABLE_MESSAGE,
            }
        )
        risk_rows.append(
            {
                "symbol": h.symbol,
                "available": h.risk_available,
                "payload": (
                    (doc or {}).get("risk", {}).get("payload")
                    if h.risk_available and isinstance(doc, dict)
                    else None
                ),
                "message": None if h.risk_available else UNAVAILABLE_MESSAGE,
            }
        )

    unique_sectors = sorted(
        {
            str(h.sector)
            for h in linked
            if h.sector not in (None, UNAVAILABLE_MESSAGE)
        }
    )

    watch_symbols = watchlist.symbols if watchlist else ()
    watch_linked = []
    watch_missing = []
    for sym in watch_symbols:
        bundle = research.get(sym)
        if bundle and (
            bundle.research_object is not None
            or bundle.report is not None
            or bundle.snapshot is not None
        ):
            watch_linked.append(
                {
                    "symbol": sym,
                    "research_object_id": bundle.research_object_id,
                    "report_id": bundle.report_id,
                    "snapshot_id": bundle.snapshot_id,
                }
            )
        else:
            watch_missing.append({"symbol": sym, "message": UNAVAILABLE_MESSAGE})

    return {
        "portfolio_summary": {
            "portfolio_id": portfolio.portfolio_id if portfolio else None,
            "holding_count": len(holdings),
            "linked_research_count": linked_count,
            "missing_research_count": len(missing),
            "weights_provided_count": sum(1 for h in holdings if h.weight is not None),
        },
        "diversification_summary": {
            "holding_count": len(holdings),
            "unique_sector_count": len(unique_sectors),
            "sectors": unique_sectors,
            "note": "Counts of holdings/sectors from linked research labels only.",
        },
        "sector_allocation": {
            "by_sector": sectors_sorted,
            "note": "Weight sums use caller-provided holding weights; sector labels from research identity when available.",
        },
        "position_concentration": {
            "top_holdings_by_weight": top,
            "note": "Ordered by caller-provided weights only — no optimisation.",
        },
        "portfolio_risk_summary": {
            "positions": risk_rows,
            "available_count": sum(1 for r in risk_rows if r["available"]),
            "unavailable_count": sum(1 for r in risk_rows if not r["available"]),
            "note": "Pass-through risk sections from linked research objects/reports.",
        },
        "margin_of_safety_summary": {
            "positions": mos_rows,
            "available_count": sum(
                1 for r in mos_rows if r["margin_of_safety"] != UNAVAILABLE_MESSAGE
            ),
            "unavailable_count": sum(
                1 for r in mos_rows if r["margin_of_safety"] == UNAVAILABLE_MESSAGE
            ),
            "note": "Pass-through MoS values from linked research — no portfolio-weighted MoS computed.",
        },
        "quality_summary": {
            "positions": quality_rows,
            "available_count": sum(1 for r in quality_rows if r["available"]),
            "unavailable_count": sum(1 for r in quality_rows if not r["available"]),
            "note": "Pass-through business quality sections — no rescoring.",
        },
        "watchlist_summary": {
            "watchlist_id": watchlist.watchlist_id if watchlist else None,
            "symbol_count": len(watch_symbols),
            "linked": watch_linked,
            "missing_research": watch_missing,
        },
        "missing_research": missing,
    }
