"""Verified, multi-source outstanding-share resolution for valuation inputs.

Only approved primary fundamental sources may supply the authoritative count.
Approved secondary sources (Screener/Yahoo Finance) are cross-checks only.
Market-data quote fields are never promoted to fundamental share-count authority.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from math import isfinite

from data_engine.source_governance import (
    PRIMARY_SOURCES,
    SECONDARY_SOURCES,
    is_approved_source,
)


@dataclass(frozen=True, slots=True)
class ShareCount:
    ticker: str
    shares: float
    as_of: date
    source: str
    verified: bool = False
    purpose: str = "fundamental"

    def __post_init__(self) -> None:
        if not self.ticker.strip() or not isfinite(self.shares) or self.shares <= 0:
            raise ValueError("share count requires a ticker and positive finite shares")
        if not self.source.strip():
            raise ValueError("share count source is required")
        if self.purpose not in {"fundamental", "cross_check", "verification"}:
            raise ValueError("share count purpose is invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker.strip().upper(),
            "shares": self.shares,
            "as_of": self.as_of.isoformat(),
            "source": self.source.strip().upper(),
            "verified": self.verified,
            "purpose": self.purpose,
        }


class ShareCountPort(ABC):
    """Port deliberately separate from financial statements and market quotes."""

    @abstractmethod
    def get_outstanding_shares(self, ticker: str) -> ShareCount | None:
        """Return a sourced share-count candidate or None."""


class InMemoryShareCountPort(ShareCountPort):
    def __init__(self, rows: tuple[ShareCount, ...] = ()) -> None:
        self._rows = {row.ticker.strip().upper(): row for row in rows}

    def get_outstanding_shares(self, ticker: str) -> ShareCount | None:
        return self._rows.get(ticker.strip().upper())


def resolve_verified_share_count(
    ticker: str,
    candidates: Iterable[ShareCount],
    *,
    tolerance: float = 0.05,
) -> ShareCount | None:
    """Choose a recent verified primary source after reconciling all candidates.

    Secondary sources are cross-checks only. Disagreement beyond tolerance
    fails closed rather than silently selecting a number.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("ticker is required")
    if not isfinite(tolerance) or tolerance < 0 or tolerance >= 1:
        raise ValueError("tolerance must be finite and between zero and one")

    accepted: list[ShareCount] = []
    for candidate in candidates:
        if candidate.ticker.strip().upper() != symbol or not candidate.verified:
            continue
        source = candidate.source.strip().upper()
        if not is_approved_source(source, purpose=candidate.purpose):
            continue
        if source in SECONDARY_SOURCES and candidate.purpose not in {"cross_check", "verification"}:
            continue
        if source not in PRIMARY_SOURCES and source not in SECONDARY_SOURCES:
            continue
        accepted.append(candidate)

    primary = [row for row in accepted if row.source.strip().upper() in PRIMARY_SOURCES]
    if not primary:
        return None
    primary.sort(key=lambda row: (row.as_of, row.source.strip().upper()), reverse=True)
    chosen = primary[0]
    for other in accepted:
        relative_delta = abs(chosen.shares - other.shares) / max(chosen.shares, other.shares)
        if relative_delta > tolerance:
            raise ValueError("verified share-count sources disagree beyond tolerance")
    return chosen


__all__ = [
    "InMemoryShareCountPort",
    "ShareCount",
    "ShareCountPort",
    "resolve_verified_share_count",
]
