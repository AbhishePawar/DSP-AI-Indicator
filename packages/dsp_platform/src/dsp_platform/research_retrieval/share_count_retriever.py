"""Verified share-count retrieval integrating with data_engine.share_count."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from data_engine import ShareCount, resolve_verified_share_count
from data_engine import (
    DEFAULT_SHARE_COUNT_MAX_AGE_DAYS,
    is_share_count_current,
)
from dsp_platform.research_retrieval.models import ShareCountEvidence

__all__ = [
    "RetrievalShareCountResolver",
    "resolve_share_count_from_evidence",
]

# Keep this list aligned with the data-engine source governance.
PRIMARY_SHARE_SOURCES = frozenset({"NSE", "BSE", "COMPANY_OFFICIAL_WEBSITE"})
SECONDARY_SHARE_SOURCES = frozenset({"SCREENER", "YAHOO_FINANCE"})


def resolve_share_count_from_evidence(
    ticker: str,
    candidates: Iterable[ShareCount],
    tolerance: float = 0.05,
    *,
    reference_date: date | None = None,
    max_age_days: int = DEFAULT_SHARE_COUNT_MAX_AGE_DAYS,
) -> ShareCountEvidence | None:
    """Resolve a verified primary count, using secondary sources only as checks.

    Unverified candidates, unrelated tickers, and unapproved sources are
    excluded before resolution. A disagreement never produces verified data.
    """
    symbol = ticker.strip().upper()
    if not symbol:
        return None

    reference = reference_date or date.today()

    if type(reference) is not date:
        raise ValueError("reference_date must be a date")

    if type(max_age_days) is not int or max_age_days < 0:
        raise ValueError("max_age_days must be a non-negative integer")

    accepted_primary: list[ShareCount] = []
    accepted_secondary: list[ShareCount] = []

    for candidate in candidates:
        if candidate.ticker.strip().upper() != symbol or not candidate.verified:
            continue

        if not is_share_count_current(
            candidate,
            reference_date=reference,
            max_age_days=max_age_days,
        ):
            continue

        source = candidate.source.strip().upper()

        if source in PRIMARY_SHARE_SOURCES and candidate.purpose == "fundamental":
            accepted_primary.append(candidate)
        elif source in SECONDARY_SHARE_SOURCES and candidate.purpose in {
            "cross_check",
            "verification",
        }:
            accepted_secondary.append(candidate)

    # Secondary evidence can never become the authoritative count.
    if not accepted_primary:
        return None

    eligible = accepted_primary + accepted_secondary

    try:
        resolved = resolve_verified_share_count(
            symbol,
            eligible,
            tolerance=tolerance,
            reference_date=reference,
            max_age_days=max_age_days,
        )
    except ValueError:
        # Preserve the primary figure for diagnostics only. It is explicitly
        # unverified because the independently verified sources disagree.
        primary = max(
            accepted_primary,
            key=lambda row: (row.as_of, row.source.strip().upper()),
        )
        return ShareCountEvidence(
            ticker=symbol,
            shares=primary.shares,
            as_of=primary.as_of.isoformat(),
            source=primary.source.strip().upper(),
            is_primary=True,
            verified=False,
            cross_checked=bool(accepted_secondary),
            discrepancy_flag=True,
            secondary_sources=tuple(
                sorted({row.source.strip().upper() for row in accepted_secondary})
            ),
        )

    if resolved is None:
        return None

    return ShareCountEvidence(
        ticker=symbol,
        shares=resolved.shares,
        as_of=resolved.as_of.isoformat(),
        source=resolved.source.strip().upper(),
        is_primary=True,
        verified=True,
        cross_checked=bool(accepted_secondary),
        discrepancy_flag=False,
        secondary_sources=tuple(
            sorted({row.source.strip().upper() for row in accepted_secondary})
        ),
    )


class RetrievalShareCountResolver:
    """Resolver service wrapper for share count integration."""

    def __init__(self, tolerance: float = 0.05) -> None:
        self.tolerance = tolerance

    def resolve(
        self,
        ticker: str,
        candidates: Iterable[ShareCount],
        *,
        reference_date: date | None = None,
    ) -> ShareCountEvidence | None:
        return resolve_share_count_from_evidence(
            ticker,
            candidates,
            tolerance=self.tolerance,
            reference_date=reference_date,
        )
