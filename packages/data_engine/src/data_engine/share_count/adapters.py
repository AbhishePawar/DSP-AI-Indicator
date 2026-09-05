"""Share-count adapters — Null (unavailable) + in-memory test fixture only.

No live vendor is selected here. FMP / Yahoo / Upstox are not share-count
providers. There is no fallback chain.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine.exceptions import ProviderRequestError
from data_engine.share_count.models import (
    ShareCountBasis,
    ShareCountField,
    ShareCountProvenance,
    ShareCountSnapshot,
    ShareCountUnit,
)
from data_engine.share_count.port import ShareCountPort, ShareCountProviderHealth
from data_engine.share_count.validation import validate_share_count_snapshot

__all__ = [
    "InMemoryShareCountAdapter",
    "NullShareCountAdapter",
    "build_default_share_count_adapter_from_env",
    "build_share_count_from_mapping",
]


def build_share_count_from_mapping(
    *,
    symbol: str,
    payload: Mapping[str, Any],
    provenance: ShareCountProvenance,
    basis: ShareCountBasis | str = ShareCountBasis.CURRENT_OUTSTANDING,
    unit: ShareCountUnit | str = ShareCountUnit.SHARES,
) -> ShareCountSnapshot:
    """Map a vendor-neutral field dict → ShareCountSnapshot."""
    basis_enum = basis if isinstance(basis, ShareCountBasis) else ShareCountBasis(basis)
    unit_enum = unit if isinstance(unit, ShareCountUnit) else ShareCountUnit(unit)
    as_of_raw = payload.get("as_of")
    as_of = as_of_raw if isinstance(as_of_raw, datetime) else None
    snapshot = ShareCountSnapshot(
        symbol=str(symbol).strip().upper(),
        exchange=(str(payload["exchange"]) if payload.get("exchange") else None),
        isin=(str(payload["isin"]).strip().upper() if payload.get("isin") else None),
        shares=ShareCountField.of(payload.get("shares")),
        basis=basis_enum,
        unit=unit_enum,
        as_of=as_of,
        provenance=provenance,
    )
    validate_share_count_snapshot(snapshot)
    return snapshot


@dataclass
class NullShareCountAdapter(ShareCountPort):
    """Always unavailable — no estimate, no derivation, no fallback."""

    _provider_id: str = "null_share_count"

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def get_share_count(self, instrument: Instrument) -> ShareCountSnapshot | None:
        _ = instrument
        return None

    def health(self) -> ShareCountProviderHealth:
        return ShareCountProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=False,
            detail="null provider — no share-count feed configured",
        )


@dataclass
class InMemoryShareCountAdapter(ShareCountPort):
    """TEST-ONLY seeded snapshots. Never invents symbols or estimates counts."""

    api_key: str | None = None
    _provider_id: str = "memory_authenticated_share_count"
    _snapshots: dict[str, ShareCountSnapshot] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, repr=False)

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def put(self, snapshot: ShareCountSnapshot) -> None:
        validate_share_count_snapshot(snapshot)
        with self._lock:
            self._snapshots[snapshot.symbol.upper()] = snapshot

    def get_share_count(self, instrument: Instrument) -> ShareCountSnapshot | None:
        if not self.api_key:
            raise ProviderRequestError(
                "memory share-count adapter requires api_key (authentication)"
            )
        with self._lock:
            return self._snapshots.get(instrument.symbol.strip().upper())

    def health(self) -> ShareCountProviderHealth:
        return ShareCountProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=bool(self.api_key),
            detail=(
                "seeded in-memory authenticated share counts (test fixture)"
                if self.api_key
                else "missing api_key"
            ),
        )


def build_default_share_count_adapter_from_env() -> ShareCountPort:
    """Select share-count adapter from environment.

    No live provider is configured in this task. Production therefore
    receives ``NullShareCountAdapter`` and valuation fails closed.

    Routes:
    - ``DSP_SHARE_COUNT_MEMORY`` (non-production only) → in-memory test adapter
    - otherwise → Null (unavailable). No FMP / Yahoo / Upstox selection.
    """
    from data_engine.connector_framework.production_profile import (
        memory_adapter_allowed,
    )

    if memory_adapter_allowed("DSP_SHARE_COUNT_MEMORY", connector="share_count"):
        api_key = (
            os.environ.get("DSP_SHARE_COUNT_API_KEY", "").strip() or "dev-memory-key"
        )
        return InMemoryShareCountAdapter(api_key=api_key)
    return NullShareCountAdapter()
