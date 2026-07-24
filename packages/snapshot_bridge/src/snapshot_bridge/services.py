"""Application services composing Data Engine lookups with snapshot bridges.

These services are optional conveniences for orchestration (Sprint 7.0).
Builders remain usable without any Data Engine service — tests and
callers that already hold contracts objects should call builders
directly.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from contracts.domain.economic_series import EconomicSeries
from data_engine import EconomicDataService, FundamentalsDataService, FundamentalsRequest
from economic import EconomicSnapshot
from fundamental import FinancialSnapshot
from snapshot_bridge.economic import EconomicSnapshotBuilder
from snapshot_bridge.financial import FinancialSnapshotBuilder

__all__ = ["EconomicBridgeService", "FinancialBridgeService"]

_DEFAULT_ECONOMIC_CODES: tuple[str, ...] = (
    "GDP",
    "CPI",
    "INTEREST_RATE",
    "PMI",
    "M2",
    "UNEMPLOYMENT",
)


class FinancialBridgeService:
    """Fetch fundamental statements and bridge them to ``FinancialSnapshot``."""

    def __init__(self, *, fundamentals: FundamentalsDataService) -> None:
        """Initialize with a Data Engine fundamentals service."""
        self._fundamentals = fundamentals

    def get_snapshot(self, request: FundamentalsRequest) -> FinancialSnapshot:
        """Retrieve statements and return an engine-native snapshot."""
        statements = self._fundamentals.get_fundamental_statements(request)
        return FinancialSnapshotBuilder.build(request.instrument, statements)


class EconomicBridgeService:
    """Fetch economic series and bridge them to ``EconomicSnapshot``."""

    def __init__(self, *, economic: EconomicDataService) -> None:
        """Initialize with a Data Engine economic service."""
        self._economic = economic

    def get_snapshot(
        self,
        *,
        country: str = "US",
        indicator_codes: Sequence[str] = _DEFAULT_ECONOMIC_CODES,
        as_of: date | None = None,
        limit: int | None = None,
        provider_name: str | None = None,
    ) -> EconomicSnapshot:
        """Retrieve available series and return an engine-native snapshot.

        Uses ``get_available_series`` so missing indicators degrade
        gracefully instead of aborting the whole snapshot.
        """
        available = self._economic.get_available_series(
            indicator_codes=tuple(indicator_codes),
            country=country,
            provider_name=provider_name,
            limit=limit,
        )
        return EconomicSnapshotBuilder.build(
            available, country=country, as_of=as_of
        )

    def get_snapshot_from_series(
        self,
        series_by_code: dict[str, EconomicSeries],
        *,
        country: str = "US",
        as_of: date | None = None,
    ) -> EconomicSnapshot:
        """Bridge an already-fetched series map (no Data Engine I/O)."""
        return EconomicSnapshotBuilder.build(
            series_by_code, country=country, as_of=as_of
        )
