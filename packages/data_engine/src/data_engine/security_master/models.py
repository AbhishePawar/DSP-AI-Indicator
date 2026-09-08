"""Provider-neutral Security Master identity models.

Authoritative listing identity is ``ISIN + MIC``, never ticker alone and
never a vendor instrument key (``NSE_EQ|…``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "EXCHANGE_MIC",
    "MIC_EXCHANGE",
    "SecurityListing",
    "SecurityMasterAuthority",
    "SecurityResolveStatus",
    "SecuritySearchStatus",
    "UNSUPPORTED_SECURITY_TYPES",
]

SecuritySearchStatus = Literal[
    "MATCHES",
    "UNKNOWN",
    "REJECTED",
    "UNSUPPORTED",
]
SecurityResolveStatus = Literal[
    "RESOLVED",
    "AMBIGUOUS",
    "UNKNOWN",
    "UNSUPPORTED",
    "REJECTED",
]

EXCHANGE_MIC = {
    "NSE": "XNSE",
    "BSE": "XBOM",
}
MIC_EXCHANGE = {mic: exchange for exchange, mic in EXCHANGE_MIC.items()}

UNSUPPORTED_SECURITY_TYPES = frozenset(
    {
        "warrant",
        "bond",
        "debenture",
        "derivative",
        "future",
        "option",
        "index",
        "mutual_fund",
        "etf",
        "preference",
        "right",
    }
)


@dataclass(frozen=True, slots=True)
class SecurityMasterAuthority:
    """Provenance for the official supported universe — not a vendor."""

    source: str
    source_type: str
    retrieved_at: str
    detail: str

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_type": self.source_type,
            "retrieved_at": self.retrieved_at,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class SecurityListing:
    """One exchange listing of an official security."""

    ticker: str
    company_name: str
    isin: str
    exchange: str
    mic: str
    security_type: str
    eligibility: bool
    currency: str = "INR"
    country: str = "IN"
    series: str | None = None
    aliases: tuple[str, ...] = ()

    @property
    def listing_id(self) -> str:
        return f"{self.isin}.{self.mic}"

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "company_name": self.company_name,
            "ticker": self.ticker,
            "isin": self.isin,
            "exchange": self.exchange,
            "mic": self.mic,
            "security_type": self.security_type,
            "eligibility": self.eligibility,
            "currency": self.currency,
            "country": self.country,
            "listing_id": self.listing_id,
            "series": self.series,
        }
