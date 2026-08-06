"""Portfolio Opportunity Finder — ranking of already-computed signals only.

Every ranking dimension reuses a value already produced elsewhere (Valuation
Engine margin of safety, business-quality stage score, risk-attribution
volatility, committee/recommendation confidence). No new score is computed.
"Highest Expected CAGR" is honestly reported unavailable: no engine in the
platform produces a forward-looking, per-company equity CAGR.
"""

from __future__ import annotations

from collections.abc import Sequence

from portfolio_intelligence_engine.enums import IntelligenceStatus
from portfolio_intelligence_engine.models import (
    HoldingSignal,
    OpportunityEntry,
    OpportunityRanking,
)

__all__ = ["rank_opportunities"]


def _rank(
    holdings: Sequence[HoldingSignal],
    *,
    key: str,
    descending: bool,
    top_n: int,
) -> tuple[OpportunityEntry, ...]:
    candidates = [h for h in holdings if getattr(h, key) is not None]
    candidates.sort(key=lambda h: getattr(h, key), reverse=descending)
    return tuple(
        OpportunityEntry(symbol=h.symbol, value=getattr(h, key), weight=h.weight)
        for h in candidates[:top_n]
    )


def rank_opportunities(
    holdings: Sequence[HoldingSignal],
    *,
    top_n: int = 5,
) -> OpportunityRanking:
    if not holdings:
        return OpportunityRanking(
            status=IntelligenceStatus.UNAVAILABLE,
            highest_margin_of_safety=(),
            highest_expected_cagr=(),
            best_quality=(),
            lowest_risk=(),
            highest_conviction=(),
            limitations=("no portfolio holdings supplied.",),
        )

    mos_ranking = _rank(holdings, key="margin_of_safety", descending=True, top_n=top_n)
    quality_ranking = _rank(holdings, key="quality_score", descending=True, top_n=top_n)
    risk_ranking = _rank(holdings, key="volatility", descending=False, top_n=top_n)
    conviction_ranking = _rank(
        holdings, key="committee_confidence", descending=True, top_n=top_n
    )

    limitations: list[str] = [
        "Data unavailable. No single-company forward-looking equity CAGR is "
        "produced by the frozen valuation/AI Committee engines — "
        "'Highest Expected CAGR' cannot be honestly ranked and is left empty.",
    ]
    if not mos_ranking:
        limitations.append("No holdings have a linked margin of safety.")
    if not quality_ranking:
        limitations.append("No holdings have a linked business-quality score.")
    if not risk_ranking:
        limitations.append(
            "No holdings have per-holding volatility (risk attribution)."
        )
    if not conviction_ranking:
        limitations.append(
            "No holdings have a linked committee/recommendation confidence."
        )

    any_available = any(
        (mos_ranking, quality_ranking, risk_ranking, conviction_ranking)
    )
    status = (
        IntelligenceStatus.UNAVAILABLE
        if not any_available
        else (
            IntelligenceStatus.COMPLETE
            if all((mos_ranking, quality_ranking, risk_ranking, conviction_ranking))
            else IntelligenceStatus.PARTIAL
        )
    )

    return OpportunityRanking(
        status=status,
        highest_margin_of_safety=mos_ranking,
        highest_expected_cagr=(),
        best_quality=quality_ranking,
        lowest_risk=risk_ranking,
        highest_conviction=conviction_ranking,
        limitations=tuple(limitations),
    )
