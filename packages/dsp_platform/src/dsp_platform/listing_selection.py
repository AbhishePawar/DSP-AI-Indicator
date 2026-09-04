"""Indian equity listing selection (Stage 4P).

DSP business policy ? not Upstox U1 identity resolution.

BSE-first / NSE-fallback applies only when the caller did not supply an
explicit exchange. U1 remains fail-closed when ``preferred_exchange`` is
absent and multiple instruments match.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "INDIAN_LISTING_EXCHANGES",
    "ListingCandidate",
    "ListingSelection",
    "ListingSelectionStatus",
    "select_indian_listing",
]

INDIAN_LISTING_EXCHANGES: frozenset[str] = frozenset({"BSE", "NSE"})

ListingSelectionStatus = Literal[
    "SELECTED",
    "NOT_FOUND",
    "AMBIGUOUS",
    "NOT_APPLICABLE",
    "UNAVAILABLE",
]


@dataclass(frozen=True, slots=True)
class ListingCandidate:
    """Venue + ISIN pair from a provider search. Not a U1 pick."""

    exchange: str
    isin: str


@dataclass(frozen=True, slots=True)
class ListingSelection:
    """Result of DSP Indian listing policy. Never silently invents a venue."""

    status: ListingSelectionStatus
    symbol: str
    exchange: str | None = None
    isin: str | None = None
    detail: str = ""

    def to_public_dict(self) -> dict[str, str | None]:
        return {
            "status": self.status,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "isin": self.isin,
            "detail": self.detail,
        }


def _norm_symbol(raw: str) -> str:
    return str(raw or "").strip().upper()


def _norm_exchange(raw: str | None) -> str | None:
    text = str(raw or "").strip().upper()
    return text or None


def _candidate_exchange(candidate: object) -> str | None:
    return _norm_exchange(getattr(candidate, "exchange", None))


def _candidate_isin(candidate: object) -> str:
    return str(getattr(candidate, "isin", "") or "").strip().upper()


def _indian_candidates(candidates: Iterable[object]) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for candidate in candidates:
        exchange = _candidate_exchange(candidate)
        if exchange not in INDIAN_LISTING_EXCHANGES:
            continue
        isin = _candidate_isin(candidate)
        rows.append((exchange, isin))
    return rows


def _unique_isins(rows: Sequence[tuple[str, str]]) -> tuple[str, ...]:
    seen: list[str] = []
    for _exchange, isin in rows:
        if not isin:
            continue
        if isin not in seen:
            seen.append(isin)
    return tuple(seen)


def select_indian_listing(
    symbol: str,
    explicit_exchange: str | None,
    candidates: Sequence[object],
) -> ListingSelection:
    """Select an Indian listing venue from exact-symbol equity candidates.

    Explicit exchange always wins and never falls back to the other venue.
    Unspecified exchange: one ISIN -> BSE if present else NSE; multiple
    ISINs -> AMBIGUOUS; no Indian candidates -> NOT_FOUND (or NOT_APPLICABLE
    when only non-Indian candidates exist).
    """
    query = _norm_symbol(symbol)
    preferred = _norm_exchange(explicit_exchange)
    pool = tuple(candidates)

    if preferred is not None and preferred not in INDIAN_LISTING_EXCHANGES:
        return ListingSelection(
            status="NOT_APPLICABLE",
            symbol=query,
            exchange=preferred,
            detail="Indian BSE-first policy does not apply to this exchange",
        )

    indian = _indian_candidates(pool)
    if preferred is not None:
        matching = [(ex, isin) for ex, isin in indian if ex == preferred]
        if not matching:
            return ListingSelection(
                status="NOT_FOUND",
                symbol=query,
                exchange=None,
                detail=f"no {preferred} listing for {query!r}",
            )
        isins = _unique_isins(matching)
        if any(not isin for _ex, isin in matching) and not isins:
            return ListingSelection(
                status="AMBIGUOUS",
                symbol=query,
                detail=f"{preferred} candidates for {query!r} lack ISIN",
            )
        if len(isins) > 1:
            return ListingSelection(
                status="AMBIGUOUS",
                symbol=query,
                detail=(
                    f"multiple securities match {query!r} on {preferred}; "
                    "not a listing-venue choice"
                ),
            )
        return ListingSelection(
            status="SELECTED",
            symbol=query,
            exchange=preferred,
            isin=isins[0] if isins else None,
            detail=f"explicit exchange {preferred}",
        )

    if not indian:
        if any(_norm_exchange(getattr(c, "exchange", None)) for c in pool):
            return ListingSelection(
                status="NOT_APPLICABLE",
                symbol=query,
                detail="no Indian (BSE/NSE) listing candidates",
            )
        return ListingSelection(
            status="NOT_FOUND",
            symbol=query,
            detail=f"no listing candidates for {query!r}",
        )

    isins = _unique_isins(indian)
    if not isins:
        return ListingSelection(
            status="AMBIGUOUS",
            symbol=query,
            detail=(
                f"Indian candidates for {query!r} lack ISIN; "
                "identity not established"
            ),
        )
    if len(isins) > 1:
        return ListingSelection(
            status="AMBIGUOUS",
            symbol=query,
            detail=(
                f"multiple ISINs match {query!r}; "
                "not a BSE/NSE venue choice for one security"
            ),
        )

    isin = isins[0]
    venues = {ex for ex, row_isin in indian if row_isin == isin}
    if "BSE" in venues:
        return ListingSelection(
            status="SELECTED",
            symbol=query,
            exchange="BSE",
            isin=isin,
            detail="BSE-first for single-ISIN dual listing",
        )
    if "NSE" in venues:
        return ListingSelection(
            status="SELECTED",
            symbol=query,
            exchange="NSE",
            isin=isin,
            detail="NSE fallback; no BSE listing for this ISIN",
        )
    return ListingSelection(
        status="NOT_FOUND",
        symbol=query,
        isin=isin,
        detail=f"no BSE or NSE listing for {query!r}",
    )
