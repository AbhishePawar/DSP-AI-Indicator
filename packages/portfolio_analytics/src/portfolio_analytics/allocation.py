"""Sector and Country allocation breakdowns.

Sector allocation is a parallel implementation to EPIC-A002's (that package
is frozen, so we cannot import from it) — same "weight grouped by declared
category" approach. Country allocation is net-new: derived from a caller-
declared ``country`` per position, or failing that a small documented
exchange -> country lookup table. Positions with neither become
"unclassified" — never guessed.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from portfolio_analytics.enums import AllocationDimension, AnalyticsStatus
from portfolio_analytics.models import (
    AllocationBreakdown,
    AllocationBucket,
    PositionInput,
)

__all__ = [
    "EXCHANGE_COUNTRY_TABLE",
    "compute_country_allocation",
    "compute_sector_allocation",
]

#: Small, explicit, documented exchange -> country table. Deliberately
#: conservative: an exchange missing from this table yields "unclassified"
#: rather than a guess.
EXCHANGE_COUNTRY_TABLE: dict[str, str] = {
    "NASDAQ": "United States",
    "NYSE": "United States",
    "AMEX": "United States",
    "NYSEARCA": "United States",
    "BATS": "United States",
    "NSE": "India",
    "BSE": "India",
    "LSE": "United Kingdom",
    "LON": "United Kingdom",
    "TSX": "Canada",
    "TSXV": "Canada",
    "ASX": "Australia",
    "HKEX": "Hong Kong",
    "SSE": "China",
    "SZSE": "China",
    "TSE": "Japan",
    "SGX": "Singapore",
    "FRA": "Germany",
    "XETRA": "Germany",
    "EPA": "France",
    "BME": "Spain",
    "SWX": "Switzerland",
}


def _group_allocation(
    positions: Sequence[PositionInput],
    *,
    dimension: AllocationDimension,
    label_of: Callable[[PositionInput], str | None],
) -> AllocationBreakdown:
    buckets: dict[str, list[str]] = {}
    bucket_weight: dict[str, float] = {}
    unclassified_weight = 0.0

    for position in positions:
        label = label_of(position)
        if label is None:
            unclassified_weight += position.weight
            continue
        buckets.setdefault(label, []).append(position.symbol)
        bucket_weight[label] = bucket_weight.get(label, 0.0) + position.weight

    result_buckets = tuple(
        AllocationBucket(label=label, weight=weight, symbols=tuple(buckets[label]))
        for label, weight in sorted(
            bucket_weight.items(), key=lambda kv: kv[1], reverse=True
        )
    )

    limitations: list[str] = []
    if unclassified_weight > 0:
        limitations.append(
            f"{unclassified_weight:.4f} of total weight has no declared "
            f"{dimension.value}; classified as unclassified rather than guessed."
        )

    if not result_buckets:
        status = AnalyticsStatus.UNAVAILABLE
    elif unclassified_weight > 0:
        status = AnalyticsStatus.PARTIAL
    else:
        status = AnalyticsStatus.COMPLETE

    return AllocationBreakdown(
        dimension=dimension,
        status=status,
        buckets=result_buckets,
        unclassified_weight=unclassified_weight,
        limitations=tuple(limitations),
    )


def compute_sector_allocation(positions: Sequence[PositionInput]) -> AllocationBreakdown:
    return _group_allocation(
        positions,
        dimension=AllocationDimension.SECTOR,
        label_of=lambda p: p.sector,
    )


def compute_country_allocation(positions: Sequence[PositionInput]) -> AllocationBreakdown:
    def _country(position: PositionInput) -> str | None:
        if position.country:
            return position.country
        if position.exchange:
            return EXCHANGE_COUNTRY_TABLE.get(position.exchange.strip().upper())
        return None

    return _group_allocation(
        positions,
        dimension=AllocationDimension.COUNTRY,
        label_of=_country,
    )
