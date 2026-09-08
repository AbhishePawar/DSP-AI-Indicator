"""Provider-neutral Security Master search and identity resolution.

Search may match ticker, company name, or alias. Final identity is always
ISIN + MIC. Never guesses, never uses Upstox keys, never silently picks
NSE vs BSE.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from data_engine.security_master.catalog import (
    SecurityMasterCatalog,
    load_default_catalog,
)
from data_engine.security_master.models import (
    EXCHANGE_MIC,
    MIC_EXCHANGE,
    SecurityListing,
    SecurityMasterAuthority,
    SecurityResolveStatus,
    SecuritySearchStatus,
    UNSUPPORTED_SECURITY_TYPES,
)

__all__ = [
    "SecurityMasterService",
    "SecurityResolveResult",
    "SecuritySearchResult",
    "is_vendor_shaped_identity",
    "normalize_security_query",
]

_YAHOO_STYLE_SUFFIX = re.compile(r"\.(NS|BO)$", re.IGNORECASE)
_VENDOR_PREFIX = re.compile(
    r"^(NSE_EQ|BSE_EQ|NSE_FO|BSE_FO|NSE_INDEX|BSE_INDEX|MCX_FO|NSE_COM)\|",
    re.IGNORECASE,
)


def is_vendor_shaped_identity(raw: str) -> bool:
    """True when the input looks like a vendor instrument key, not a ticker."""
    text = str(raw or "").strip()
    if not text:
        return False
    if "|" in text:
        return True
    return bool(_VENDOR_PREFIX.match(text))


def normalize_security_query(raw: str) -> str:
    """Harmless formatting only — does not invent an exchange."""
    text = str(raw or "").strip()
    text = _YAHOO_STYLE_SUFFIX.sub("", text)
    return " ".join(text.split())


def _norm_exchange(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip().upper()
    if not text:
        return None
    if text in MIC_EXCHANGE:
        return MIC_EXCHANGE[text]
    if text in EXCHANGE_MIC:
        return text
    return text


@dataclass(frozen=True, slots=True)
class SecuritySearchResult:
    status: SecuritySearchStatus
    query: str
    results: tuple[SecurityListing, ...]
    authority: SecurityMasterAuthority
    detail: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "status": self.status,
            "query": self.query,
            "results": [item.to_public_dict() for item in self.results],
            "authority": self.authority.to_public_dict(),
            "detail": self.detail,
            "message": None if self.status == "MATCHES" else self.detail,
        }


@dataclass(frozen=True, slots=True)
class SecurityResolveResult:
    status: SecurityResolveStatus
    query: str
    identity: SecurityListing | None
    candidates: tuple[SecurityListing, ...]
    authority: SecurityMasterAuthority
    detail: str
    exchange: str | None = None
    isin: str | None = None
    mic: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "status": self.status,
            "query": self.query,
            "exchange": self.exchange,
            "isin": self.isin,
            "mic": self.mic,
            "identity": None
            if self.identity is None
            else self.identity.to_public_dict(),
            "candidates": [item.to_public_dict() for item in self.candidates],
            "authority": self.authority.to_public_dict(),
            "detail": self.detail,
            "message": None if self.status == "RESOLVED" else self.detail,
        }


@dataclass
class SecurityMasterService:
    catalog: SecurityMasterCatalog = field(default_factory=load_default_catalog)

    def search(
        self,
        query: str,
        *,
        exchange: str | None = None,
        limit: int = 25,
    ) -> SecuritySearchResult:
        authority = self.catalog.authority
        raw = str(query or "")
        if is_vendor_shaped_identity(raw):
            return SecuritySearchResult(
                status="REJECTED",
                query=raw.strip(),
                results=(),
                authority=authority,
                detail="Vendor-shaped identity is not an authoritative Security Master key.",
            )
        normalized = normalize_security_query(raw)
        if not normalized:
            return SecuritySearchResult(
                status="UNKNOWN",
                query=raw.strip(),
                results=(),
                authority=authority,
                detail="UNKNOWN",
            )
        exchange_norm = _norm_exchange(exchange)
        matches = self._match(normalized, exchange=exchange_norm)
        if not matches:
            return SecuritySearchResult(
                status="UNKNOWN",
                query=normalized,
                results=(),
                authority=authority,
                detail="UNKNOWN",
            )
        if all(not item.eligibility for item in matches):
            return SecuritySearchResult(
                status="UNSUPPORTED",
                query=normalized,
                results=matches[: max(1, limit)],
                authority=authority,
                detail="UNSUPPORTED",
            )
        return SecuritySearchResult(
            status="MATCHES",
            query=normalized,
            results=matches[: max(1, limit)],
            authority=authority,
            detail="MATCHES",
        )

    def resolve(
        self,
        query: str,
        *,
        exchange: str | None = None,
        isin: str | None = None,
        mic: str | None = None,
    ) -> SecurityResolveResult:
        authority = self.catalog.authority
        raw = str(query or "")
        exchange_norm = _norm_exchange(exchange)
        mic_norm = str(mic).strip().upper() if mic else None
        if mic_norm and not exchange_norm:
            exchange_norm = MIC_EXCHANGE.get(mic_norm)
        isin_norm = str(isin).strip().upper() if isin else None

        if is_vendor_shaped_identity(raw):
            return SecurityResolveResult(
                status="REJECTED",
                query=raw.strip(),
                identity=None,
                candidates=(),
                authority=authority,
                detail="Vendor-shaped identity is not an authoritative Security Master key.",
                exchange=exchange_norm,
                isin=isin_norm,
                mic=mic_norm,
            )

        normalized = normalize_security_query(raw)
        if isin_norm and mic_norm:
            exact = self._by_listing_id(f"{isin_norm}.{mic_norm}")
            if exact is None:
                return SecurityResolveResult(
                    status="UNKNOWN",
                    query=normalized or isin_norm,
                    identity=None,
                    candidates=(),
                    authority=authority,
                    detail="UNKNOWN",
                    exchange=exchange_norm,
                    isin=isin_norm,
                    mic=mic_norm,
                )
            return self._resolved(normalized or exact.ticker, exact, exchange_norm, isin_norm, mic_norm)

        if not normalized and not isin_norm:
            return SecurityResolveResult(
                status="UNKNOWN",
                query=raw.strip(),
                identity=None,
                candidates=(),
                authority=authority,
                detail="UNKNOWN",
                exchange=exchange_norm,
                isin=isin_norm,
                mic=mic_norm,
            )

        matches = self._match(normalized or isin_norm or "", exchange=exchange_norm)
        if isin_norm:
            matches = tuple(item for item in matches if item.isin == isin_norm)
        if mic_norm:
            matches = tuple(item for item in matches if item.mic == mic_norm)

        if not matches:
            return SecurityResolveResult(
                status="UNKNOWN",
                query=normalized,
                identity=None,
                candidates=(),
                authority=authority,
                detail="UNKNOWN",
                exchange=exchange_norm,
                isin=isin_norm,
                mic=mic_norm,
            )

        eligible = tuple(item for item in matches if item.eligibility)
        if not eligible:
            return SecurityResolveResult(
                status="UNSUPPORTED",
                query=normalized,
                identity=None,
                candidates=matches,
                authority=authority,
                detail="UNSUPPORTED",
                exchange=exchange_norm,
                isin=isin_norm,
                mic=mic_norm,
            )

        mics = {item.mic for item in eligible}
        isins = {item.isin for item in eligible}
        if len(eligible) == 1:
            only = eligible[0]
            return self._resolved(normalized, only, exchange_norm, isin_norm, mic_norm)
        if len(mics) > 1 or len(isins) > 1:
            return SecurityResolveResult(
                status="AMBIGUOUS",
                query=normalized,
                identity=None,
                candidates=eligible,
                authority=authority,
                detail="AMBIGUOUS",
                exchange=exchange_norm,
                isin=isin_norm,
                mic=mic_norm,
            )
        return self._resolved(normalized, eligible[0], exchange_norm, isin_norm, mic_norm)

    def _resolved(
        self,
        query: str,
        listing: SecurityListing,
        exchange: str | None,
        isin: str | None,
        mic: str | None,
    ) -> SecurityResolveResult:
        if listing.security_type in UNSUPPORTED_SECURITY_TYPES or not listing.eligibility:
            return SecurityResolveResult(
                status="UNSUPPORTED",
                query=query,
                identity=None,
                candidates=(listing,),
                authority=self.catalog.authority,
                detail="UNSUPPORTED",
                exchange=exchange,
                isin=isin,
                mic=mic,
            )
        return SecurityResolveResult(
            status="RESOLVED",
            query=query,
            identity=listing,
            candidates=(listing,),
            authority=self.catalog.authority,
            detail="RESOLVED",
            exchange=exchange or listing.exchange,
            isin=isin or listing.isin,
            mic=mic or listing.mic,
        )

    def _by_listing_id(self, listing_id: str) -> SecurityListing | None:
        for item in self.catalog.all():
            if item.listing_id == listing_id:
                return item
        return None

    def _match(
        self, query: str, *, exchange: str | None
    ) -> tuple[SecurityListing, ...]:
        needle = query.strip()
        ticker_needle = needle.upper().replace(" ", "")
        name_needle = needle.lower()
        allow_name = len(name_needle) >= 3
        scored: list[tuple[int, str, str, SecurityListing]] = []
        for item in self.catalog.all():
            if exchange and item.exchange != exchange:
                continue
            rank = self._rank(item, ticker_needle, name_needle, allow_name)
            if rank is None:
                continue
            scored.append((rank, item.ticker, item.mic, item))
        scored.sort(key=lambda row: (row[0], row[1], row[2]))
        return tuple(row[3] for row in scored)

    def _rank(
        self,
        item: SecurityListing,
        ticker_needle: str,
        name_needle: str,
        allow_name: bool,
    ) -> int | None:
        ticker = item.ticker.upper()
        name = item.company_name.lower()
        aliases = tuple(alias.lower() for alias in item.aliases)
        if ticker == ticker_needle:
            return 0
        if ticker.startswith(ticker_needle):
            return 1
        if allow_name and name_needle in name:
            return 2
        if allow_name and any(name_needle in alias for alias in aliases):
            return 3
        if item.isin.upper() == ticker_needle:
            return 4
        return None
