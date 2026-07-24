"""Resolve market capitalization for Valuation Engine MoS.

Market cap is never invented. Sources (in priority order):

1. ``AnalysisRequest.market_cap`` explicit override
2. ``FinancialSnapshot.latest.extra_line_items`` entry with key
   ``market_capitalization`` (canonical from data_engine normalizers)
"""

from __future__ import annotations

from contracts import MARKET_CAPITALIZATION_KEY
from fundamental import FinancialSnapshot
from orchestration.models import AnalysisRequest
from valuation import MarketSnapshot

__all__ = ["resolve_market_snapshot"]


def resolve_market_snapshot(
    request: AnalysisRequest,
    snapshot: FinancialSnapshot,
) -> MarketSnapshot | None:
    """Build an optional :class:`MarketSnapshot` for margin of safety.

    Returns ``None`` when no usable market capitalization is available
    so the Valuation Engine reports MoS as unavailable rather than
    inventing a figure.
    """
    if request.market_cap is not None:
        return MarketSnapshot(market_cap=float(request.market_cap))

    extras = dict(snapshot.latest.extra_line_items)
    raw = extras.get(MARKET_CAPITALIZATION_KEY)
    if raw is None:
        return None
    try:
        cap = float(raw)
    except (TypeError, ValueError):
        return None
    if cap < 0:
        return None
    return MarketSnapshot(market_cap=cap)
