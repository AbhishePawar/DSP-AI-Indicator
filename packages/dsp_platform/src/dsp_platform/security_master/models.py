"""Provider-neutral Security Master records.

Permanent listing identity is ISIN + MIC, not ticker. Ticker is a search
attribute. DSP analysis eligibility is classification, not financial-data proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "EXCHANGE_MIC",
    "EligibilityStatus",
    "ListingStatus",
    "MatchKind",
    "ResolutionStatus",
    "SearchHit",
    "SearchOutcome",
    "SecurityMasterRecord",
    "SecurityType",
    "SnapshotStatus",
    "SourceDocument",
    "SourceTrace",
    "UniverseCounts",
    "UniverseSnapshot",
]

EXCHANGE_MIC = {"NSE": "XNSE", "BSE": "XBOM"}


class SecurityType(StrEnum):
    COMMON_EQUITY = "common_equity"
    SME_EQUITY = "sme_equity"
    ETF = "etf"
    REIT = "reit"
    INVIT = "invit"
    PREFERENCE = "preference"
    WARRANT = "warrant"
    OTHER = "other"
    UNKNOWN = "unknown"


class ListingStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"
    UNKNOWN = "UNKNOWN"


class EligibilityStatus(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    UNSUPPORTED_SECURITY_TYPE = "UNSUPPORTED_SECURITY_TYPE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"
    IDENTITY_INCOMPLETE = "IDENTITY_INCOMPLETE"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    OTHER_EXCLUSION = "OTHER_EXCLUSION"


class SnapshotStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    FAILED = "FAILED"
    SOURCE_DATE_UNKNOWN = "SOURCE_DATE_UNKNOWN"


class MatchKind(StrEnum):
    EXACT_ISIN = "EXACT_ISIN"
    EXACT_SYMBOL = "EXACT_SYMBOL"
    EXACT_CODE = "EXACT_CODE"
    PREFIX_SYMBOL = "PREFIX_SYMBOL"
    NAME_SUBSTRING = "NAME_SUBSTRING"


class ResolutionStatus(StrEnum):
    EXACT = "EXACT"
    DUAL_LISTING_CANDIDATES = "DUAL_LISTING_CANDIDATES"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class SourceDocument:
    source_id: str
    exchange: str
    document_kind: str
    uri: str
    body: bytes
    retrieved_at: str
    last_modified: str
    content_type: str
    status: int
    error: str = ""


@dataclass(frozen=True, slots=True)
class SourceTrace:
    source_id: str
    exchange: str
    document_kind: str
    uri: str
    retrieved_at: str
    source_date: str
    content_hash: str
    record_count: int
    status: str
    last_modified: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "exchange": self.exchange,
            "document_kind": self.document_kind,
            "uri": self.uri,
            "retrieved_at": self.retrieved_at,
            "source_date": self.source_date,
            "content_hash": self.content_hash,
            "record_count": self.record_count,
            "status": self.status,
            "last_modified": self.last_modified,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class SecurityMasterRecord:
    listing_id: str
    issuer_id: str
    company_name: str
    legal_name: str
    trading_symbol: str
    exchange: str
    mic: str
    isin: str
    exchange_security_code: str
    series: str
    security_type: SecurityType
    listing_status: ListingStatus
    trading_status: str
    eligibility_status: EligibilityStatus
    dsp_eligible: bool
    country: str
    source: str
    source_document: str
    source_date: str
    retrieved_at: str
    snapshot_id: str
    identity_ok: bool
    exclusion_reason: str = ""
    uniqueness_flags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "issuer_id": self.issuer_id,
            "company_name": self.company_name,
            "legal_name": self.legal_name,
            "trading_symbol": self.trading_symbol,
            "exchange": self.exchange,
            "mic": self.mic,
            "isin": self.isin,
            "exchange_security_code": self.exchange_security_code,
            "series": self.series,
            "security_type": str(self.security_type),
            "listing_status": str(self.listing_status),
            "trading_status": self.trading_status,
            "eligibility_status": str(self.eligibility_status),
            "dsp_eligible": self.dsp_eligible,
            "country": self.country,
            "source": self.source,
            "source_document": self.source_document,
            "source_date": self.source_date,
            "retrieved_at": self.retrieved_at,
            "snapshot_id": self.snapshot_id,
            "identity_ok": self.identity_ok,
            "exclusion_reason": self.exclusion_reason,
            "uniqueness_flags": list(self.uniqueness_flags),
        }

    def to_search_dict(self) -> dict[str, Any]:
        return {
            "listing_id": self.listing_id,
            "issuer_id": self.issuer_id,
            "company_name": self.company_name,
            "legal_name": self.legal_name,
            "trading_symbol": self.trading_symbol,
            "exchange": self.exchange,
            "mic": self.mic,
            "isin": self.isin or None,
            "exchange_security_code": self.exchange_security_code or None,
            "series": self.series or None,
            "security_type": str(self.security_type),
            "listing_status": str(self.listing_status),
            "eligibility_status": str(self.eligibility_status),
            "dsp_eligible": self.dsp_eligible,
            "identity_ok": self.identity_ok,
        }


def record_from_dict(raw: dict[str, Any]) -> SecurityMasterRecord:
    return SecurityMasterRecord(
        listing_id=str(raw.get("listing_id") or ""),
        issuer_id=str(raw.get("issuer_id") or ""),
        company_name=str(raw.get("company_name") or ""),
        legal_name=str(raw.get("legal_name") or ""),
        trading_symbol=str(raw.get("trading_symbol") or ""),
        exchange=str(raw.get("exchange") or ""),
        mic=str(raw.get("mic") or ""),
        isin=str(raw.get("isin") or ""),
        exchange_security_code=str(raw.get("exchange_security_code") or ""),
        series=str(raw.get("series") or ""),
        security_type=_enum(SecurityType, raw.get("security_type"), SecurityType.UNKNOWN),
        listing_status=_enum(ListingStatus, raw.get("listing_status"), ListingStatus.UNKNOWN),
        trading_status=str(raw.get("trading_status") or ""),
        eligibility_status=_enum(
            EligibilityStatus, raw.get("eligibility_status"), EligibilityStatus.OTHER_EXCLUSION
        ),
        dsp_eligible=bool(raw.get("dsp_eligible")),
        country=str(raw.get("country") or ""),
        source=str(raw.get("source") or ""),
        source_document=str(raw.get("source_document") or ""),
        source_date=str(raw.get("source_date") or "UNKNOWN"),
        retrieved_at=str(raw.get("retrieved_at") or ""),
        snapshot_id=str(raw.get("snapshot_id") or ""),
        identity_ok=bool(raw.get("identity_ok")),
        exclusion_reason=str(raw.get("exclusion_reason") or ""),
        uniqueness_flags=tuple(str(item) for item in (raw.get("uniqueness_flags") or ())),
    )


def _enum(cls: type, value: object, default: object):
    text = str(value or "").strip()
    if not text:
        return default
    try:
        return cls(text)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class UniverseCounts:
    nse_source_rows: int
    bse_source_rows: int
    unique_nse_securities: int
    unique_bse_securities: int
    unique_isins: int
    dual_listed: int
    nse_only: int
    bse_only: int
    equity: int
    sme: int
    etf: int
    reit: int
    invit: int
    preference: int
    warrant: int
    other: int
    active: int
    inactive: int
    suspended: int
    unknown_status: int
    dsp_eligible: int
    dsp_ineligible: int
    identity_ambiguous: int
    identity_incomplete: int
    rows_with_isin: int
    rows_without_isin: int
    rows_with_symbol: int
    rows_without_symbol: int
    malformed_retained: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "nse_source_rows": self.nse_source_rows,
            "bse_source_rows": self.bse_source_rows,
            "unique_nse_securities": self.unique_nse_securities,
            "unique_bse_securities": self.unique_bse_securities,
            "unique_isins": self.unique_isins,
            "dual_listed": self.dual_listed,
            "nse_only": self.nse_only,
            "bse_only": self.bse_only,
            "equity": self.equity,
            "sme": self.sme,
            "etf": self.etf,
            "reit": self.reit,
            "invit": self.invit,
            "preference": self.preference,
            "warrant": self.warrant,
            "other": self.other,
            "active": self.active,
            "inactive": self.inactive,
            "suspended": self.suspended,
            "unknown_status": self.unknown_status,
            "dsp_eligible": self.dsp_eligible,
            "dsp_ineligible": self.dsp_ineligible,
            "identity_ambiguous": self.identity_ambiguous,
            "identity_incomplete": self.identity_incomplete,
            "rows_with_isin": self.rows_with_isin,
            "rows_without_isin": self.rows_without_isin,
            "rows_with_symbol": self.rows_with_symbol,
            "rows_without_symbol": self.rows_without_symbol,
            "malformed_retained": self.malformed_retained,
        }


@dataclass(frozen=True, slots=True)
class UniverseSnapshot:
    snapshot_id: str
    retrieved_at: str
    source_date: str
    content_hash: str
    record_count: int
    status: SnapshotStatus
    sources: tuple[SourceTrace, ...]
    counts: UniverseCounts
    records: tuple[SecurityMasterRecord, ...] = field(default=(), repr=False)
    error: str = ""

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "retrieved_at": self.retrieved_at,
            "source_date": self.source_date,
            "content_hash": self.content_hash,
            "record_count": self.record_count,
            "status": str(self.status),
            "error": self.error or None,
            "sources": [item.to_dict() for item in self.sources],
            "counts": self.counts.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class SearchHit:
    record: SecurityMasterRecord
    match_kind: MatchKind

    def to_dict(self) -> dict[str, Any]:
        payload = self.record.to_search_dict()
        payload["match_kind"] = str(self.match_kind)
        return payload


@dataclass(frozen=True, slots=True)
class SearchOutcome:
    query: str
    resolution: ResolutionStatus
    candidates: tuple[SearchHit, ...]
    snapshot_id: str
    source_date: str
    retrieved_at: str
    available: bool
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "resolution": str(self.resolution),
            "candidates": [hit.to_dict() for hit in self.candidates],
            "snapshot_id": self.snapshot_id or None,
            "source_date": self.source_date or None,
            "retrieved_at": self.retrieved_at or None,
            "available": self.available,
            "message": self.message,
        }
