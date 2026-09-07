"""Deterministic Security Master search. Fuzzy ranking is not authoritative."""

from __future__ import annotations

from dsp_platform.security_master.models import (
    MatchKind,
    ResolutionStatus,
    SearchHit,
    SearchOutcome,
    SecurityMasterRecord,
    UniverseSnapshot,
)
from dsp_platform.security_master.parse import is_valid_isin

__all__ = ["resolve_exact", "search_snapshot"]


def search_snapshot(
    snapshot: UniverseSnapshot | None,
    query: str,
    *,
    limit: int = 20,
) -> SearchOutcome:
    text = query.strip()
    if snapshot is None:
        return SearchOutcome(
            query=text,
            resolution=ResolutionStatus.UNAVAILABLE,
            candidates=(),
            snapshot_id="",
            source_date="",
            retrieved_at="",
            available=False,
            message="Data unavailable.",
        )
    if not text:
        return SearchOutcome(
            query=text,
            resolution=ResolutionStatus.UNKNOWN,
            candidates=(),
            snapshot_id=snapshot.snapshot_id,
            source_date=snapshot.source_date,
            retrieved_at=snapshot.retrieved_at,
            available=True,
            message="Enter a ticker, company name, ISIN, or security code.",
        )
    hits = _collect_hits(snapshot.records, text)
    resolution = _resolution(hits, text)
    message = _message(resolution)
    return SearchOutcome(
        query=text,
        resolution=resolution,
        candidates=tuple(hits[: max(1, min(limit, 50))]),
        snapshot_id=snapshot.snapshot_id,
        source_date=snapshot.source_date,
        retrieved_at=snapshot.retrieved_at,
        available=True,
        message=message,
    )


def resolve_exact(
    snapshot: UniverseSnapshot | None,
    *,
    listing_id: str = "",
    isin: str = "",
    exchange: str = "",
    symbol: str = "",
) -> SearchOutcome:
    if snapshot is None:
        return search_snapshot(None, symbol or isin or listing_id)
    lid = listing_id.strip()
    if lid:
        matches = [row for row in snapshot.records if row.listing_id == lid]
        return _from_records(snapshot, lid, matches, prefer_exact=True)
    want_isin = isin.strip().upper()
    want_ex = exchange.strip().upper()
    want_sym = symbol.strip().upper()
    matches = []
    for row in snapshot.records:
        if want_isin and row.isin != want_isin:
            continue
        if want_ex and row.exchange != want_ex:
            continue
        if want_sym and row.trading_symbol != want_sym:
            continue
        if not (want_isin or want_ex or want_sym):
            continue
        matches.append(row)
    query = want_sym or want_isin or lid
    return _from_records(snapshot, query, matches, prefer_exact=True)


def _from_records(
    snapshot: UniverseSnapshot,
    query: str,
    matches: list[SecurityMasterRecord],
    *,
    prefer_exact: bool,
) -> SearchOutcome:
    hits = tuple(
        SearchHit(record=row, match_kind=MatchKind.EXACT_ISIN if is_valid_isin(query) else MatchKind.EXACT_SYMBOL)
        for row in matches
    )
    resolution = _resolution(hits, query) if hits else ResolutionStatus.UNKNOWN
    if prefer_exact and len(hits) == 1:
        resolution = ResolutionStatus.EXACT
    return SearchOutcome(
        query=query,
        resolution=resolution,
        candidates=hits,
        snapshot_id=snapshot.snapshot_id,
        source_date=snapshot.source_date,
        retrieved_at=snapshot.retrieved_at,
        available=True,
        message=_message(resolution),
    )


def _collect_hits(
    records: tuple[SecurityMasterRecord, ...], query: str
) -> list[SearchHit]:
    needle = query.strip()
    upper = needle.upper()
    lower = needle.lower()
    hits: list[SearchHit] = []
    seen: set[str] = set()

    def add(row: SecurityMasterRecord, kind: MatchKind) -> None:
        if row.listing_id in seen:
            return
        seen.add(row.listing_id)
        hits.append(SearchHit(record=row, match_kind=kind))

    if is_valid_isin(upper):
        for row in records:
            if row.isin == upper:
                add(row, MatchKind.EXACT_ISIN)
        return hits
    for row in records:
        if row.trading_symbol == upper:
            add(row, MatchKind.EXACT_SYMBOL)
        elif row.exchange_security_code == upper or row.exchange_security_code == needle:
            add(row, MatchKind.EXACT_CODE)
    if hits:
        return hits
    for row in records:
        if row.trading_symbol.startswith(upper) and upper:
            add(row, MatchKind.PREFIX_SYMBOL)
    for row in records:
        if lower in (row.company_name or "").lower() or lower in (row.legal_name or "").lower():
            add(row, MatchKind.NAME_SUBSTRING)
    return hits


def _resolution(hits: tuple[SearchHit, ...] | list[SearchHit], _query: str) -> ResolutionStatus:
    if not hits:
        return ResolutionStatus.UNKNOWN
    exact = [
        hit
        for hit in hits
        if hit.match_kind in {MatchKind.EXACT_ISIN, MatchKind.EXACT_SYMBOL, MatchKind.EXACT_CODE}
    ]
    pool = exact or list(hits)
    if len(pool) == 1:
        return ResolutionStatus.EXACT
    isins = {hit.record.isin for hit in pool if hit.record.isin}
    if len(isins) == 1 and len({hit.record.listing_id for hit in pool}) > 1:
        return ResolutionStatus.DUAL_LISTING_CANDIDATES
    if len({hit.record.listing_id for hit in pool}) > 1:
        return ResolutionStatus.AMBIGUOUS
    return ResolutionStatus.EXACT


def _message(resolution: ResolutionStatus) -> str:
    if resolution is ResolutionStatus.EXACT:
        return ""
    if resolution is ResolutionStatus.DUAL_LISTING_CANDIDATES:
        return "Multiple exchange listings match — select the exact security."
    if resolution is ResolutionStatus.AMBIGUOUS:
        return "Multiple securities match — select the exact security."
    if resolution is ResolutionStatus.UNKNOWN:
        return "No exact security in the official universe."
    return "Data unavailable."
