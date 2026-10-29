"""Verified share-count retrieval integrating with data_engine.share_count."""

from __future__ import annotations

from collections.abc import Iterable

from data_engine import ShareCount, resolve_verified_share_count
from dsp_platform.research_retrieval.models import ShareCountEvidence

__all__ = [
    "RetrievalShareCountResolver",
    "resolve_share_count_from_evidence",
]


def resolve_share_count_from_evidence(
    ticker: str,
    candidates: Iterable[ShareCount],
    tolerance: float = 0.05,
) -> ShareCountEvidence | None:
    """Resolve authoritative share count using data_engine.share_count rules."""
    symbol = ticker.strip().upper()
    cand_list = list(candidates)
    if not cand_list:
        return None

    # Separate primary candidates and secondary cross-checks
    primary_candidates = [
        c
        for c in cand_list
        if c.purpose == "fundamental"
        and c.source in {"NSE", "BSE", "SEC", "COMPANY_OFFICIAL_WEBSITE"}
    ]
    secondary_candidates = [
        c for c in cand_list if c.purpose in {"cross_check", "verification"}
    ]

    if not primary_candidates:
        # No primary source evidence available -> Fail closed!
        return None

    try:
        resolved = resolve_verified_share_count(symbol, cand_list, tolerance=tolerance)
    except ValueError:
        resolved = None

    if resolved is None:
        # Material disagreement between primary and secondary sources
        primary = primary_candidates[0]
        return ShareCountEvidence(
            ticker=symbol,
            shares=primary.shares,
            as_of=primary.as_of.isoformat(),
            source=primary.source,
            is_primary=True,
            verified=False,
            cross_checked=True,
            discrepancy_flag=True,
            secondary_sources=tuple(s.source for s in secondary_candidates),
        )

    return ShareCountEvidence(
        ticker=symbol,
        shares=resolved.shares,
        as_of=resolved.as_of.isoformat(),
        source=resolved.source,
        is_primary=True,
        verified=True,
        cross_checked=len(secondary_candidates) > 0,
        discrepancy_flag=False,
        secondary_sources=tuple(s.source for s in secondary_candidates),
    )


class RetrievalShareCountResolver:
    """Resolver service wrapper for share count integration."""

    def __init__(self, tolerance: float = 0.05) -> None:
        self.tolerance = tolerance

    def resolve(
        self,
        ticker: str,
        candidates: Iterable[ShareCount],
    ) -> ShareCountEvidence | None:
        return resolve_share_count_from_evidence(
            ticker, candidates, tolerance=self.tolerance
        )
