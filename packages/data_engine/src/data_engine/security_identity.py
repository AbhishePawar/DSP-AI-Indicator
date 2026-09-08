"""Security Master identity authority (SIMPLE-14G).

Ticker-only vendor guessing is forbidden. This module never constructs
``NSE_EQ`` / ``BSE_EQ`` / ``instrument_key`` / ``TCS.NS``.

Without a listing catalog, identity is request-declared: ticker plus any
caller-supplied exchange / ISIN / MIC. Dual-listed ambiguity is only
raised when a catalog contains multiple listings for the same ticker and
the caller omitted exchange.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

__all__ = [
    "IdentityStatus",
    "SecurityIdentity",
    "SecurityIdentityPort",
    "SecurityListing",
    "CatalogSecurityMaster",
    "RequestDeclaredSecurityMaster",
    "default_security_master",
    "resolve_security_identity",
    "set_security_master_for_tests",
]


class IdentityStatus(StrEnum):
    RESOLVED = "RESOLVED"
    UNKNOWN = "UNKNOWN"
    AMBIGUOUS = "AMBIGUOUS"
    UNSUPPORTED = "UNSUPPORTED"
    REJECTED = "REJECTED"


_ORDINARY_EQUITY = frozenset({"EQ", "EQUITY", "ORDINARY", "COMMON"})
_FORBIDDEN_VENDOR_KEYS = ("instrument_key", "nse_eq", "bse_eq")


@dataclass(frozen=True, slots=True)
class SecurityListing:
    """One catalog row. Tests inject listings; production catalog may be empty."""

    ticker: str
    exchange: str
    isin: str = ""
    mic: str = ""
    company: str = ""
    security_type: str = "EQUITY"
    listing_status: str = "LISTED"


@dataclass(frozen=True, slots=True)
class SecurityIdentity:
    ticker: str
    company: str = ""
    isin: str = ""
    mic: str = ""
    exchange: str = ""
    security_type: str = ""
    listing_status: str = ""
    status: IdentityStatus = IdentityStatus.UNKNOWN
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "ticker": self.ticker,
            "company": self.company,
            "isin": self.isin,
            "mic": self.mic,
            "exchange": self.exchange,
            "security_type": self.security_type,
            "listing_status": self.listing_status,
            "status": self.status.value,
            "detail": self.detail,
        }


class SecurityIdentityPort(Protocol):
    def resolve(
        self,
        *,
        ticker: str,
        exchange: str | None = None,
        isin: str | None = None,
        mic: str | None = None,
        company: str | None = None,
        vendor_hints: dict[str, str] | None = None,
    ) -> SecurityIdentity: ...


def _norm(value: str | None) -> str:
    return str(value or "").strip().upper()


def _reject_vendor_hints(hints: dict[str, str] | None) -> str | None:
    if not hints:
        return None
    for key, raw in hints.items():
        lowered = str(key or "").strip().lower()
        if lowered in _FORBIDDEN_VENDOR_KEYS or lowered.replace("-", "_") in {
            "instrument_key",
        }:
            return f"rejected vendor identity hint {key!r}"
        text = str(raw or "").strip().upper()
        if text.startswith("NSE_EQ") or text.startswith("BSE_EQ"):
            return "rejected vendor segment identity"
    return None


@dataclass
class RequestDeclaredSecurityMaster:
    """Identity from the request only — never guesses exchange or ISIN."""

    def resolve(
        self,
        *,
        ticker: str,
        exchange: str | None = None,
        isin: str | None = None,
        mic: str | None = None,
        company: str | None = None,
        vendor_hints: dict[str, str] | None = None,
    ) -> SecurityIdentity:
        rejected = _reject_vendor_hints(vendor_hints)
        symbol = _norm(ticker)
        if rejected:
            return SecurityIdentity(
                ticker=symbol,
                status=IdentityStatus.REJECTED,
                detail=rejected,
            )
        if not symbol:
            return SecurityIdentity(
                ticker="",
                status=IdentityStatus.UNKNOWN,
                detail="ticker required",
            )
        ex = _norm(exchange)
        isin_n = _norm(isin)
        mic_n = _norm(mic)
        if isin_n and mic_n:
            status = IdentityStatus.RESOLVED
            detail = "request-declared ISIN+MIC"
        elif ex:
            status = IdentityStatus.UNKNOWN
            detail = "exchange declared; ISIN+MIC not verified"
        else:
            status = IdentityStatus.UNKNOWN
            detail = "ticker only; exchange/ISIN/MIC not verified"
        return SecurityIdentity(
            ticker=symbol,
            company=str(company or "").strip(),
            isin=isin_n,
            mic=mic_n,
            exchange=ex,
            security_type="EQUITY",
            listing_status="",
            status=status,
            detail=detail,
        )


@dataclass
class CatalogSecurityMaster:
    """Optional listing catalog. Does not invent rows for unknown tickers."""

    listings: tuple[SecurityListing, ...] = ()
    fallback: SecurityIdentityPort = field(
        default_factory=RequestDeclaredSecurityMaster
    )

    def resolve(
        self,
        *,
        ticker: str,
        exchange: str | None = None,
        isin: str | None = None,
        mic: str | None = None,
        company: str | None = None,
        vendor_hints: dict[str, str] | None = None,
    ) -> SecurityIdentity:
        rejected = _reject_vendor_hints(vendor_hints)
        symbol = _norm(ticker)
        if rejected:
            return SecurityIdentity(
                ticker=symbol,
                status=IdentityStatus.REJECTED,
                detail=rejected,
            )
        if not symbol:
            return self.fallback.resolve(
                ticker=ticker,
                exchange=exchange,
                isin=isin,
                mic=mic,
                company=company,
                vendor_hints=vendor_hints,
            )
        ex = _norm(exchange)
        matches = [row for row in self.listings if _norm(row.ticker) == symbol]
        if ex:
            matches = [row for row in matches if _norm(row.exchange) == ex]
        if not matches:
            return self.fallback.resolve(
                ticker=ticker,
                exchange=exchange,
                isin=isin,
                mic=mic,
                company=company,
                vendor_hints=vendor_hints,
            )
        if len(matches) > 1:
            exchanges = ",".join(sorted({_norm(m.exchange) for m in matches}))
            return SecurityIdentity(
                ticker=symbol,
                status=IdentityStatus.AMBIGUOUS,
                detail=f"multiple listings require exchange ({exchanges})",
            )
        row = matches[0]
        if _norm(row.security_type) not in _ORDINARY_EQUITY and _norm(
            row.security_type
        ):
            return SecurityIdentity(
                ticker=symbol,
                exchange=_norm(row.exchange),
                isin=_norm(row.isin),
                mic=_norm(row.mic),
                company=row.company,
                security_type=row.security_type,
                listing_status=row.listing_status,
                status=IdentityStatus.UNSUPPORTED,
                detail=f"unsupported security type {row.security_type!r}",
            )
        return SecurityIdentity(
            ticker=symbol,
            company=row.company or str(company or "").strip(),
            isin=_norm(row.isin) or _norm(isin),
            mic=_norm(row.mic) or _norm(mic),
            exchange=_norm(row.exchange),
            security_type=row.security_type or "EQUITY",
            listing_status=row.listing_status or "LISTED",
            status=IdentityStatus.RESOLVED,
            detail="security master listing",
        )


_DEFAULT_MASTER: SecurityIdentityPort = RequestDeclaredSecurityMaster()


def default_security_master() -> SecurityIdentityPort:
    return _DEFAULT_MASTER


def set_security_master_for_tests(master: SecurityIdentityPort | None) -> None:
    global _DEFAULT_MASTER
    _DEFAULT_MASTER = master or RequestDeclaredSecurityMaster()


def resolve_security_identity(
    *,
    ticker: str,
    exchange: str | None = None,
    isin: str | None = None,
    mic: str | None = None,
    company: str | None = None,
    vendor_hints: dict[str, str] | None = None,
) -> SecurityIdentity:
    return default_security_master().resolve(
        ticker=ticker,
        exchange=exchange,
        isin=isin,
        mic=mic,
        company=company,
        vendor_hints=vendor_hints,
    )
