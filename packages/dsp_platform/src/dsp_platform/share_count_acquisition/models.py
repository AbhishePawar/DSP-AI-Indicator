"""Provenance-preserving share-count evidence objects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from dsp_platform.share_count_refresh import InstrumentIdentity

__all__ = [
    "ExchangeAcquisitionRequest",
    "ExchangeAcquisitionResult",
    "ShareCountEvidenceClaim",
]


@dataclass(frozen=True, slots=True)
class ShareCountEvidenceClaim:
    """One sourced claim. Dates are never silently substituted."""

    source_id: str
    source_tier: str
    issuer: str
    identity: InstrumentIdentity
    document_reference: str
    retrieved_at: datetime
    publication_at: date | None
    as_of: date | None
    effective_date: date | None
    claim_type: str
    claim_value: str
    evidence_excerpt: str


@dataclass(frozen=True, slots=True)
class ExchangeAcquisitionRequest:
    identity: InstrumentIdentity
    start: date
    end: date
    retrieved_at: datetime
    scrip_code: str | None = None


@dataclass(frozen=True, slots=True)
class ExchangeAcquisitionResult:
    identity: InstrumentIdentity
    source_id: str
    requested_start: date
    requested_end: date
    retrieved_at: datetime
    corporate_actions: tuple[Mapping[str, Any], ...]
    announcements: tuple[Mapping[str, Any], ...]
    pagination_exhausted: bool
    date_range_explicit: bool
    truncated: bool
    page_count: int
    record_count: int
    source_url: str
    evidence_reference: str
    pages_fetched: int


def nse_date(value: date) -> str:
    return f"{value.day:02d}-{value.month:02d}-{value.year:04d}"


def bse_date(value: date) -> str:
    return value.strftime("%Y%m%d")
