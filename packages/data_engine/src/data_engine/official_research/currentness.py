"""Currentness, cache, price/share compatibility, and typed research failures."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from data_engine.official_research.models import CAPITAL_EVENT_TYPES, FailureStatus

__all__ = [
    "CapitalEvent",
    "EvidenceCache",
    "cache_key",
    "corporate_action_horizon_status",
    "currentness_label",
    "evaluate_freshness",
    "is_current",
    "judge_currentness",
    "market_cap_status",
    "derived_market_cap_input_status",
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


def currentness_label(
    *,
    field: str,
    as_of: date | None,
    retrieved_at: datetime,
    current_through: date | None = None,
    freshness_status: str | None = None,
    corporate_action_status: str | None = None,
    later_filings: tuple[date, ...] = (),
    corporate_actions: tuple[CapitalEvent, ...] = (),
    valuation_date: date | None = None,
) -> str:
    """retrieved_at is not as_of. Annual fields may stay CURRENT after retrieval."""
    if corporate_action_status == "CONFLICT":
        return "CONFLICT"
    if as_of is None:
        return "UNKNOWN"
    if freshness_status == "FAIL" or corporate_action_status in {
        "FAIL",
        "REFRESH_REQUIRED",
    }:
        return "STALE"
    if field == "shares_outstanding":
        return "CURRENT"
    if field == "eod_close":
        if not is_current(
            as_of=as_of,
            current_through=current_through or as_of,
            retrieved_at=retrieved_at,
            later_filings=later_filings,
            corporate_actions=corporate_actions,
            valuation_date=valuation_date,
        ):
            return "STALE"
        return "CURRENT"
    if freshness_status == "PASS":
        return "CURRENT"
    if freshness_status == "UNKNOWN":
        return "UNKNOWN"
    return "CURRENT" if as_of is not None else "UNKNOWN"


def field_needs_ca_currentness(field: str) -> bool:
    return field in {"shares_outstanding", "eod_close", "last_price", "price"}


def evaluate_freshness(
    *,
    field: str,
    as_of: date | None,
    retrieved_at: datetime,
    current_through: date | None = None,
    freshness_status: str | None = None,
    corporate_action_status: str | None = None,
    later_filings: tuple[date, ...] = (),
    corporate_actions: tuple[CapitalEvent, ...] = (),
    valuation_date: date | None = None,
    required_as_of: date | None = None,
    freshness_class: str | None = None,
) -> str:
    """Field-specific freshness. retrieved_at is never the financial as_of."""
    if corporate_action_status == "CONFLICT":
        return "UNKNOWN"
    if as_of is None:
        return "UNKNOWN"
    if freshness_status == "FAIL" or corporate_action_status in {
        "FAIL",
        "REFRESH_REQUIRED",
    }:
        return "REFRESH_REQUIRED"
    as_of_day = valuation_date or retrieved_at.date()
    kind = freshness_class or (
        "session_or_latest_eod"
        if field in {"eod_close", "price"}
        else "current_research_window"
        if field == "last_price"
        else "latest_count_plus_ca_review"
        if field == "shares_outstanding"
        else "latest_audited_period"
    )
    if required_as_of is not None and as_of < required_as_of:
        return "REFRESH_REQUIRED"
    if kind == "current_research_window" and as_of < as_of_day:
        return "REFRESH_REQUIRED"
    if kind == "session_or_latest_eod":
        if required_as_of is not None and as_of != required_as_of:
            return "REFRESH_REQUIRED"
        if not is_current(
            as_of=as_of,
            current_through=current_through or as_of,
            retrieved_at=retrieved_at,
            later_filings=later_filings,
            corporate_actions=corporate_actions,
            valuation_date=valuation_date,
        ):
            return "REFRESH_REQUIRED"
        return "CURRENT"
    if kind == "latest_count_plus_ca_review":
        if not is_current(
            as_of=as_of,
            current_through=date.max,
            retrieved_at=retrieved_at,
            later_filings=later_filings,
            corporate_actions=corporate_actions,
            valuation_date=valuation_date,
        ):
            return "REFRESH_REQUIRED"
        return "CURRENT"
    if later_filings and any(filing > as_of for filing in later_filings):
        return "STALE"
    if freshness_status == "UNKNOWN":
        return "UNKNOWN"
    return "CURRENT"


def corporate_action_horizon_status(
    *,
    as_of: date | None,
    checked_through: date | None,
    research_horizon: date | None,
) -> str:
    """CA review must cover the research horizon. The horizon is never extended silently."""
    if as_of is None or research_horizon is None:
        return "UNKNOWN"
    if checked_through is None:
        return "REFRESH_REQUIRED"
    if checked_through < research_horizon:
        return "REFRESH_REQUIRED"
    return "CURRENT"


def judge_currentness(
    *,
    field: str,
    as_of: date | None,
    retrieved_at: datetime,
    current_through: date | None = None,
    last_verified_at: datetime | None = None,
    document_date: date | None = None,
    freshness_status: str | None = None,
    corporate_action_status: str | None = None,
    later_filings: tuple[date, ...] = (),
    corporate_actions: tuple[CapitalEvent, ...] = (),
    valuation_date: date | None = None,
    required_as_of: date | None = None,
    freshness_class: str | None = None,
    price_kind: str | None = None,
    ca_checked_through: date | None = None,
    research_horizon: date | None = None,
) -> str:
    """Deterministic currentness. retrieved_at being recent does not make a fact current."""
    _ = last_verified_at
    _ = document_date
    if corporate_action_status == "CONFLICT":
        return "CONFLICT"
    if as_of is None:
        return "UNKNOWN"
    if price_kind == "PREVIOUS_CLOSE" and field in {"eod_close", "last_price", "price"}:
        return "UNKNOWN"
    if price_kind == "HISTORICAL" and field in {"eod_close", "last_price", "price"}:
        return "UNKNOWN"
    if field == "shares_outstanding":
        horizon = research_horizon or valuation_date or retrieved_at.date()
        ca_status = corporate_action_horizon_status(
            as_of=as_of,
            checked_through=ca_checked_through,
            research_horizon=horizon,
        )
        if ca_status != "CURRENT":
            return ca_status
    label = evaluate_freshness(
        field=field,
        as_of=as_of,
        retrieved_at=retrieved_at,
        current_through=current_through,
        freshness_status=freshness_status,
        corporate_action_status=corporate_action_status,
        later_filings=later_filings,
        corporate_actions=corporate_actions,
        valuation_date=valuation_date,
        required_as_of=required_as_of,
        freshness_class=freshness_class,
    )
    if label == "STALE":
        return "REFRESH_REQUIRED"
    if label in {"CURRENT", "REFRESH_REQUIRED", "UNKNOWN", "CONFLICT"}:
        return label
    return "UNKNOWN"


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


def derived_market_cap_input_status(
    *,
    price_as_of: date,
    shares_as_of: date,
    corporate_actions: tuple[CapitalEvent, ...] = (),
    shares_current_through: date | None = None,
    ca_checked_through: date | None = None,
) -> FailureStatus:
    """Allow market cap when the share CA horizon covers the price date and no events intervene."""
    through = ca_checked_through or shares_current_through or shares_as_of
    if price_as_of > through:
        return "REFRESH_REQUIRED"
    earlier = price_as_of if price_as_of < shares_as_of else shares_as_of
    later = shares_as_of if price_as_of < shares_as_of else price_as_of
    for event in corporate_actions:
        if not event.capital_changing:
            continue
        if earlier < event.event_date <= later:
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
