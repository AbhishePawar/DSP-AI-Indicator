"""Centralized DSP financial-source allowlist and provenance contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SourceType = Literal["primary", "secondary"]
PRIMARY_SOURCES = frozenset({"NSE", "BSE", "CAMS", "CDSL", "COMPANY_OFFICIAL_WEBSITE", "IBPF"})
SECONDARY_SOURCES = frozenset({"SCREENER", "YAHOO_FINANCE"})
APPROVED_SOURCES = PRIMARY_SOURCES | SECONDARY_SOURCES
# Market-data licensing is purpose-specific. Upstox is permitted for quotes and
# historical market series only; it is not an approved financial-statement source.
MARKET_DATA_SOURCES = frozenset({"UPSTOX"})
MARKET_DATA_PURPOSES = frozenset({"market_quote", "historical_series", "historical_market_data"})


@dataclass(frozen=True, slots=True)
class DataProvenance:
    source: str
    source_type: SourceType
    purpose: str
    period: str | None = None
    retrieved_at: str | None = None
    verified: bool = False

    def __post_init__(self) -> None:
        source = self.source.strip().upper()
        if source not in APPROVED_SOURCES:
            raise ValueError(f"unapproved financial source: {source}")
        expected: SourceType = "primary" if source in PRIMARY_SOURCES else "secondary"
        if self.source_type != expected:
            raise ValueError(f"source type mismatch for {source}")
        if not self.purpose.strip():
            raise ValueError("provenance purpose must not be empty")
        object.__setattr__(self, "source", source)


def is_approved_source(source: str, *, purpose: str = "") -> bool:
    normalized = source.strip().upper()
    normalized_purpose = purpose.strip().lower()
    if normalized in MARKET_DATA_SOURCES:
        return normalized_purpose in MARKET_DATA_PURPOSES
    if normalized not in APPROVED_SOURCES:
        return False
    if normalized in SECONDARY_SOURCES and purpose.strip().lower() not in {"cross_check", "sanity_check", "verification"}:
        return False
    return True


__all__ = ["APPROVED_SOURCES", "MARKET_DATA_PURPOSES", "MARKET_DATA_SOURCES", "PRIMARY_SOURCES", "SECONDARY_SOURCES", "DataProvenance", "is_approved_source"]
