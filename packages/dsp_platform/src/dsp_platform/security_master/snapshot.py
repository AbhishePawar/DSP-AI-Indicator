"""Build a versioned universe snapshot from parsed official source documents."""

from __future__ import annotations

import hashlib
from collections import Counter
from datetime import UTC, datetime

from dsp_platform.security_master.classify import (
    classify_bse_group,
    classify_nse_series,
    eligibility_for,
)
from dsp_platform.security_master.models import (
    EligibilityStatus,
    ListingStatus,
    SecurityMasterRecord,
    SecurityType,
    SnapshotStatus,
    SourceDocument,
    SourceTrace,
    UniverseCounts,
    UniverseSnapshot,
)
from dsp_platform.security_master.parse import (
    ParsedListing,
    is_valid_isin,
    parse_bse_json,
    parse_nse_csv,
    source_date_from_last_modified,
)

__all__ = ["MINIMUM_SOURCE_ROWS", "build_snapshot", "content_sha256", "empty_counts"]

# Production floors from SIMPLE-13 live files (2026-09-07). Test fixtures are
# smaller and must call build_snapshot without enforce_minimums.
MINIMUM_SOURCE_ROWS = {
    "nse_equity": 1000,
    "nse_sme": 100,
    "nse_etf": 50,
    "bse_active": 1000,
    "bse_suspended": 50,
    "bse_delisted": 100,
}


def content_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def empty_counts() -> UniverseCounts:
    return _empty_counts()


def build_snapshot(
    documents: tuple[SourceDocument, ...],
    *,
    retrieved_at: str | None = None,
    snapshot_id: str | None = None,
    enforce_minimums: bool = False,
) -> UniverseSnapshot:
    retrieved = retrieved_at or datetime.now(tz=UTC).isoformat()
    traces: list[SourceTrace] = []
    parsed_rows: list[tuple[ParsedListing, str, str]] = []
    failed = False
    errors: list[str] = []

    for doc in documents:
        source_date = source_date_from_last_modified(doc.last_modified)
        digest = content_sha256(doc.body)
        if doc.error or doc.status != 200:
            failed = True
            errors.append(f"{doc.source_id}: fetch failed")
            traces.append(
                SourceTrace(
                    source_id=doc.source_id,
                    exchange=doc.exchange,
                    document_kind=doc.document_kind,
                    uri=doc.uri,
                    retrieved_at=doc.retrieved_at or retrieved,
                    source_date=source_date,
                    content_hash=digest,
                    record_count=0,
                    status="FAILED",
                    last_modified=doc.last_modified,
                    error=doc.error or f"HTTP {doc.status}",
                )
            )
            continue
        if not doc.body:
            failed = True
            errors.append(f"{doc.source_id}: empty file")
            traces.append(
                SourceTrace(
                    source_id=doc.source_id,
                    exchange=doc.exchange,
                    document_kind=doc.document_kind,
                    uri=doc.uri,
                    retrieved_at=doc.retrieved_at or retrieved,
                    source_date=source_date,
                    content_hash=digest,
                    record_count=0,
                    status="FAILED",
                    last_modified=doc.last_modified,
                    error="empty file",
                )
            )
            continue
        rows, parse_error = _parse_document(doc)
        if parse_error:
            failed = True
            errors.append(f"{doc.source_id}: {parse_error}")
            traces.append(
                SourceTrace(
                    source_id=doc.source_id,
                    exchange=doc.exchange,
                    document_kind=doc.document_kind,
                    uri=doc.uri,
                    retrieved_at=doc.retrieved_at or retrieved,
                    source_date=source_date,
                    content_hash=digest,
                    record_count=0,
                    status="FAILED",
                    last_modified=doc.last_modified,
                    error=parse_error,
                )
            )
            continue
        min_rows = MINIMUM_SOURCE_ROWS.get(doc.source_id, 0) if enforce_minimums else 0
        if min_rows and len(rows) < min_rows:
            failed = True
            errors.append(
                f"{doc.source_id}: unexpectedly tiny dataset ({len(rows)} < {min_rows})"
            )
            traces.append(
                SourceTrace(
                    source_id=doc.source_id,
                    exchange=doc.exchange,
                    document_kind=doc.document_kind,
                    uri=doc.uri,
                    retrieved_at=doc.retrieved_at or retrieved,
                    source_date=source_date,
                    content_hash=digest,
                    record_count=len(rows),
                    status="FAILED",
                    last_modified=doc.last_modified,
                    error=f"unexpectedly tiny dataset ({len(rows)} < {min_rows})",
                )
            )
            continue
        traces.append(
            SourceTrace(
                source_id=doc.source_id,
                exchange=doc.exchange,
                document_kind=doc.document_kind,
                uri=doc.uri,
                retrieved_at=doc.retrieved_at or retrieved,
                source_date=source_date,
                content_hash=digest,
                record_count=len(rows),
                status="OK",
                last_modified=doc.last_modified,
            )
        )
        for row in rows:
            parsed_rows.append((row, source_date, doc.retrieved_at or retrieved))

    sid = snapshot_id or _snapshot_id(retrieved, traces)
    if failed:
        return UniverseSnapshot(
            snapshot_id=sid,
            retrieved_at=retrieved,
            source_date=_combined_source_date(traces),
            content_hash=_snapshot_hash(traces),
            record_count=0,
            status=SnapshotStatus.FAILED,
            sources=tuple(traces),
            counts=_empty_counts(),
            records=(),
            error="; ".join(errors),
        )

    records = _to_records(parsed_rows, snapshot_id=sid)
    counts = _counts(records, traces)
    source_date = _combined_source_date(traces)
    status = (
        SnapshotStatus.SOURCE_DATE_UNKNOWN
        if source_date == "UNKNOWN"
        else SnapshotStatus.ACCEPTED
    )
    return UniverseSnapshot(
        snapshot_id=sid,
        retrieved_at=retrieved,
        source_date=source_date,
        content_hash=_snapshot_hash(traces),
        record_count=len(records),
        status=status,
        sources=tuple(traces),
        counts=counts,
        records=records,
    )


def _parse_document(doc: SourceDocument) -> tuple[tuple[ParsedListing, ...], str]:
    if doc.exchange == "NSE":
        _fields, rows, error = parse_nse_csv(
            doc.body, source_id=doc.source_id, document_kind=doc.document_kind
        )
        return (rows, error)
    status = {
        "equity_active": "ACTIVE",
        "equity_suspended": "SUSPENDED",
        "equity_delisted": "DELISTED",
    }.get(doc.document_kind, "UNKNOWN")
    return parse_bse_json(
        doc.body,
        source_id=doc.source_id,
        document_kind=doc.document_kind,
        listing_status=status,
    )


def _to_records(
    rows: list[tuple[ParsedListing, str, str]],
    *,
    snapshot_id: str,
) -> tuple[SecurityMasterRecord, ...]:
    seen_isin_mic: dict[str, int] = {}
    seen_code: dict[str, int] = {}
    seen_symbol: dict[str, int] = {}
    prepared: list[tuple[ParsedListing, str, str, tuple[str, ...], str, str]] = []

    for row, source_date, retrieved_at in rows:
        isin = row.isin if is_valid_isin(row.isin) else ""
        symbol = row.trading_symbol.strip().upper()
        mic = row.mic.strip().upper()
        listing_id = _listing_id(isin, mic, row.exchange, symbol, row.exchange_security_code, row.series)
        flags: list[str] = []
        if isin:
            key = f"{isin}:{mic}"
            if key in seen_isin_mic:
                flags.append("duplicate_isin_mic")
            seen_isin_mic[key] = seen_isin_mic.get(key, 0) + 1
        if row.exchange_security_code:
            code_key = f"{row.exchange}:{row.exchange_security_code}"
            if code_key in seen_code:
                flags.append("duplicate_security_code")
            seen_code[code_key] = seen_code.get(code_key, 0) + 1
        if symbol:
            sym_key = f"{row.exchange}:{symbol}"
            if sym_key in seen_symbol:
                flags.append("duplicate_symbol_exchange")
            seen_symbol[sym_key] = seen_symbol.get(sym_key, 0) + 1
        issuer_id = isin if isin else f"NOISIN:{listing_id}"
        prepared.append(
            (row, source_date, retrieved_at, tuple(flags), listing_id, issuer_id)
        )

    records: list[SecurityMasterRecord] = []
    used_ids: dict[str, int] = {}
    for row, source_date, retrieved_at, flags, listing_id, issuer_id in prepared:
        seen_n = used_ids.get(listing_id, 0)
        used_ids[listing_id] = seen_n + 1
        if seen_n:
            listing_id = f"{listing_id}#dup{seen_n}"
        security_type = _type_for(row)
        listing_status = _listing_status(row.listing_status)
        identity_ok = bool(
            is_valid_isin(row.isin)
            and row.trading_symbol.strip()
            and row.mic.strip()
            and row.exchange.strip()
            and not row.parse_error
        )
        eligibility, dsp_eligible, reason = eligibility_for(
            security_type=security_type,
            listing_status=listing_status,
            identity_ok=identity_ok,
            uniqueness_flags=flags,
        )
        if row.parse_error and not reason:
            reason = row.parse_error
        records.append(
            SecurityMasterRecord(
                listing_id=listing_id,
                issuer_id=issuer_id,
                company_name=row.company_name,
                legal_name=row.legal_name or row.company_name,
                trading_symbol=row.trading_symbol.strip().upper(),
                exchange=row.exchange,
                mic=row.mic,
                isin=row.isin if is_valid_isin(row.isin) else row.isin,
                exchange_security_code=row.exchange_security_code,
                series=row.series,
                security_type=security_type,
                listing_status=listing_status,
                trading_status=row.trading_status,
                eligibility_status=eligibility,
                dsp_eligible=dsp_eligible,
                country="IN",
                source=row.exchange,
                source_document=row.source_id,
                source_date=source_date,
                retrieved_at=retrieved_at,
                snapshot_id=snapshot_id,
                identity_ok=identity_ok,
                exclusion_reason=reason,
                uniqueness_flags=flags,
            )
        )
    return tuple(records)


def _type_for(row: ParsedListing) -> SecurityType:
    if row.exchange == "NSE":
        return classify_nse_series(row.series, row.document_kind)
    return classify_bse_group(row.series, row.document_kind)


def _listing_status(raw: str) -> ListingStatus:
    text = raw.strip().upper()
    if text in {"ACTIVE", "LISTED"}:
        return ListingStatus.ACTIVE
    if text == "SUSPENDED":
        return ListingStatus.SUSPENDED
    if text == "DELISTED":
        return ListingStatus.DELISTED
    return ListingStatus.UNKNOWN


def _listing_id(
    isin: str,
    mic: str,
    exchange: str,
    symbol: str,
    code: str,
    series: str,
) -> str:
    if isin and mic:
        return f"{isin}:{mic}"
    parts = ["NOISIN", exchange, symbol or "-", code or "-", series or "-"]
    return ":".join(parts)


def _counts(
    records: tuple[SecurityMasterRecord, ...],
    traces: list[SourceTrace],
) -> UniverseCounts:
    nse_source = sum(t.record_count for t in traces if t.exchange == "NSE")
    bse_source = sum(t.record_count for t in traces if t.exchange == "BSE")
    nse_ids = {r.listing_id for r in records if r.exchange == "NSE"}
    bse_ids = {r.listing_id for r in records if r.exchange == "BSE"}
    nse_isins = {r.isin for r in records if r.exchange == "NSE" and is_valid_isin(r.isin)}
    bse_isins = {r.isin for r in records if r.exchange == "BSE" and is_valid_isin(r.isin)}
    types = Counter(r.security_type for r in records)
    statuses = Counter(r.listing_status for r in records)
    elig = Counter(r.eligibility_status for r in records)
    return UniverseCounts(
        nse_source_rows=nse_source,
        bse_source_rows=bse_source,
        unique_nse_securities=len(nse_ids),
        unique_bse_securities=len(bse_ids),
        unique_isins=len({r.isin for r in records if is_valid_isin(r.isin)}),
        dual_listed=len(nse_isins & bse_isins),
        nse_only=len(nse_isins - bse_isins),
        bse_only=len(bse_isins - nse_isins),
        equity=types[SecurityType.COMMON_EQUITY],
        sme=types[SecurityType.SME_EQUITY],
        etf=types[SecurityType.ETF],
        reit=types[SecurityType.REIT],
        invit=types[SecurityType.INVIT],
        preference=types[SecurityType.PREFERENCE],
        warrant=types[SecurityType.WARRANT],
        other=types[SecurityType.OTHER] + types[SecurityType.UNKNOWN],
        active=statuses[ListingStatus.ACTIVE],
        inactive=statuses[ListingStatus.DELISTED],
        suspended=statuses[ListingStatus.SUSPENDED],
        unknown_status=statuses[ListingStatus.UNKNOWN],
        dsp_eligible=sum(1 for r in records if r.dsp_eligible),
        dsp_ineligible=sum(1 for r in records if not r.dsp_eligible),
        identity_ambiguous=elig[EligibilityStatus.IDENTITY_AMBIGUOUS],
        identity_incomplete=elig[EligibilityStatus.IDENTITY_INCOMPLETE],
        rows_with_isin=sum(1 for r in records if is_valid_isin(r.isin)),
        rows_without_isin=sum(1 for r in records if not is_valid_isin(r.isin)),
        rows_with_symbol=sum(1 for r in records if r.trading_symbol),
        rows_without_symbol=sum(1 for r in records if not r.trading_symbol),
        malformed_retained=sum(
            1 for r in records if (not r.identity_ok) or r.uniqueness_flags
        ),
    )


def _empty_counts() -> UniverseCounts:
    return UniverseCounts(
        nse_source_rows=0,
        bse_source_rows=0,
        unique_nse_securities=0,
        unique_bse_securities=0,
        unique_isins=0,
        dual_listed=0,
        nse_only=0,
        bse_only=0,
        equity=0,
        sme=0,
        etf=0,
        reit=0,
        invit=0,
        preference=0,
        warrant=0,
        other=0,
        active=0,
        inactive=0,
        suspended=0,
        unknown_status=0,
        dsp_eligible=0,
        dsp_ineligible=0,
        identity_ambiguous=0,
        identity_incomplete=0,
        rows_with_isin=0,
        rows_without_isin=0,
        rows_with_symbol=0,
        rows_without_symbol=0,
        malformed_retained=0,
    )


def _combined_source_date(traces: list[SourceTrace]) -> str:
    dates = sorted({item.source_date for item in traces if item.source_date not in {"", "UNKNOWN"}})
    if not dates:
        return "UNKNOWN"
    return dates[-1]


def _snapshot_hash(traces: list[SourceTrace]) -> str:
    material = "|".join(
        f"{item.source_id}:{item.content_hash}:{item.retrieved_at}:{item.source_date}"
        for item in traces
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _snapshot_id(retrieved_at: str, traces: list[SourceTrace]) -> str:
    digest = _snapshot_hash(traces)[:12]
    stamp = retrieved_at.replace(":", "").replace("-", "")[:15]
    return f"univ_{stamp}_{digest}"
