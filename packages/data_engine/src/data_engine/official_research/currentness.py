"""Currentness, cache, price/share compatibility, and typed research failures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from data_engine.official_research.models import CAPITAL_EVENT_TYPES, FailureStatus

__all__ = [
    "CapitalEvent",
    "EvidenceCache",
    "cache_key",
    "is_current",
    "market_cap_status",
]


@dataclass(frozen=True, slots=True)
class CapitalEvent:
    event_type: str
    event_date: date
    source_url: str | None = None
    capital_changing: bool = True

    def __post_init__(self) -> None:
        if self.event_type not in CAPITAL_EVENT_TYPES:
            raise ValueError(f"unknown capital event type {self.event_type!r}")


def is_current(
    *,
    as_of: date | None,
    current_through: date | None,
    retrieved_at: datetime,
    later_filings: tuple[date, ...] = (),
    corporate_actions: tuple[CapitalEvent, ...] = (),
    valuation_date: date | None = None,
) -> bool:
    """retrieved_today does not imply current_today."""
    if as_of is None:
        return False
    as_of_day = valuation_date or retrieved_at.date()
    if current_through is not None and as_of_day > current_through:
        return False
    if any(filing > as_of for filing in later_filings):
        return False
    for event in corporate_actions:
        if (
            event.capital_changing
            and event.event_date > as_of
            and event.event_date <= as_of_day
        ):
            return False
    return True


def market_cap_status(
    *,
    price_as_of: date,
    shares_as_of: date,
    corporate_actions: tuple[CapitalEvent, ...] = (),
    shares_current_through: date | None = None,
) -> FailureStatus:
    through = shares_current_through or shares_as_of
    if price_as_of > through:
        if corporate_actions:
            later = price_as_of
            earlier = through
            for event in corporate_actions:
                if not event.capital_changing:
                    continue
                if event.event_date == date.max:
                    return "REFRESH_REQUIRED"
                if earlier < event.event_date <= later:
                    return "REFRESH_REQUIRED"
            return "REFRESH_REQUIRED"
        return "REFRESH_REQUIRED"
    if price_as_of == shares_as_of:
        return "VERIFIED"
    later = price_as_of if price_as_of > shares_as_of else shares_as_of
    earlier = shares_as_of if shares_as_of < price_as_of else price_as_of
    for event in corporate_actions:
        if not event.capital_changing:
            continue
        if event.event_date == date.max:
            return "REFRESH_REQUIRED"
        if earlier < event.event_date <= later:
            return "REFRESH_REQUIRED"
    if shares_as_of != price_as_of:
        return "REFRESH_REQUIRED"
    return "VERIFIED"


def cache_key(
    *,
    isin: str,
    mic: str,
    field: str,
    period: str | None,
    source: str,
    document_hash: str = "",
) -> str:
    return "|".join(
        (
            isin.strip().upper(),
            mic.strip().upper(),
            field.strip(),
            (period or "").strip(),
            source.strip(),
            document_hash.strip(),
        )
    )


@dataclass
class CacheEntry:
    value: object
    as_of: date | None
    current_through: date | None
    source: str
    retrieved_at: datetime
    corporate_actions: tuple[CapitalEvent, ...] = ()
    later_filings: tuple[date, ...] = ()


class EvidenceCache:
    """Verified-evidence cache that never bypasses currentness."""

    def __init__(self) -> None:
        self._items: dict[str, CacheEntry] = {}

    def put(self, key: str, entry: CacheEntry) -> None:
        self._items[key] = entry

    def get(
        self,
        key: str,
        *,
        retrieved_at: datetime,
        extra_actions: tuple[CapitalEvent, ...] = (),
        extra_filings: tuple[date, ...] = (),
    ) -> CacheEntry | None:
        entry = self._items.get(key)
        if entry is None:
            return None
        actions = entry.corporate_actions + extra_actions
        filings = entry.later_filings + extra_filings
        if not is_current(
            as_of=entry.as_of,
            current_through=entry.current_through,
            retrieved_at=retrieved_at,
            later_filings=filings,
            corporate_actions=actions,
        ):
            return None
        return entry
