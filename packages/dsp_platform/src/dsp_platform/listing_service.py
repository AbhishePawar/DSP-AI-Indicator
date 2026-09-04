"""Orchestrate Indian listing selection before exchange-gated U1 resolve.

Searches provider candidates without a preferred exchange, applies DSP
BSE-first policy, then callers pass the selected venue through the existing
Stage 4I ``exchange`` / ``preferred_exchange`` handoff.

Does not change ticker-only statements/quote: those still call U1 without
an exchange and remain AMBIGUOUS for dual-listed names.
"""

from __future__ import annotations

from collections.abc import Sequence
from threading import Lock
from typing import Any

from data_engine.upstox_instrument_resolver import (
    UpstoxInstrumentResolver,
    UpstoxResolveRequest,
    normalize_user_symbol,
)
from dsp_platform.listing_selection import (
    ListingCandidate,
    ListingSelection,
    select_indian_listing,
)

__all__ = [
    "candidates_from_resolve_result",
    "reset_listing_resolver_for_tests",
    "select_listing_for_symbol",
]

_LOCK = Lock()
_RESOLVER: UpstoxInstrumentResolver | None = None


def reset_listing_resolver_for_tests(
    resolver: UpstoxInstrumentResolver | None = None,
) -> None:
    """Replace or clear the process-local search resolver (tests only)."""
    global _RESOLVER
    with _LOCK:
        _RESOLVER = resolver


def _resolver() -> UpstoxInstrumentResolver:
    global _RESOLVER
    with _LOCK:
        if _RESOLVER is None:
            _RESOLVER = UpstoxInstrumentResolver()
        return _RESOLVER


def candidates_from_resolve_result(
    result: Any, symbol: str
) -> tuple[ListingCandidate, ...]:
    """Keep exact-symbol candidates only; ignore leftover non-exact search rows."""
    query = normalize_user_symbol(symbol)
    exact: list[ListingCandidate] = []
    for raw in getattr(result, "candidates", ()) or ():
        trading = str(getattr(raw, "trading_symbol", "") or "").strip().upper()
        display = str(getattr(raw, "display_symbol", "") or "").strip().upper()
        if query and trading != query and display != query:
            continue
        exact.append(
            ListingCandidate(
                exchange=str(getattr(raw, "exchange", "") or ""),
                isin=str(getattr(raw, "isin", "") or ""),
            )
        )
    return tuple(exact)


def select_listing_for_symbol(
    symbol: str,
    *,
    explicit_exchange: str | None = None,
    candidates: Sequence[object] | None = None,
) -> ListingSelection:
    """Run listing policy. Fetches U1 candidates only when none are supplied.

    U1 is invoked without ``preferred_exchange`` so it never silently picks
    BSE/NSE. Dual-listed TCS search remains AMBIGUOUS at U1; this layer then
    selects a venue for subsequent exchange-gated requests.
    """
    query = normalize_user_symbol(symbol)
    if not query:
        return ListingSelection(
            status="NOT_FOUND",
            symbol="",
            detail="empty symbol",
        )

    if candidates is None:
        result = _resolver().resolve(UpstoxResolveRequest(symbol=query))
        status = str(getattr(result, "status", "") or "")
        if status == "UNAVAILABLE":
            return ListingSelection(
                status="UNAVAILABLE",
                symbol=query,
                detail=str(getattr(result, "detail", "") or "provider unavailable"),
            )
        if status == "REJECTED":
            return ListingSelection(
                status="UNAVAILABLE",
                symbol=query,
                detail=str(
                    getattr(result, "detail", "") or "resolver rejected request"
                ),
            )
        candidates = candidates_from_resolve_result(result, query)

    return select_indian_listing(query, explicit_exchange, tuple(candidates))
