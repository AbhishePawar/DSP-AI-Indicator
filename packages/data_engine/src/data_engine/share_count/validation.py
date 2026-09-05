"""Validate authenticated share-count snapshots — never invent replacements."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.share_count.models import (
    ShareCountBasis,
    ShareCountField,
    ShareCountSnapshot,
    ShareCountUnit,
)

__all__ = [
    "assert_share_count_identity",
    "validate_share_count_snapshot",
]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _normalize_identity(value: str | None) -> str:
    return str(value or "").strip().upper()


def validate_share_count_snapshot(snapshot: ShareCountSnapshot) -> None:
    """Reject structurally invalid snapshots. Never invent replacements."""
    if not snapshot.symbol or not str(snapshot.symbol).strip():
        raise InvalidProviderDataError("share count missing symbol")
    if not snapshot.provenance.provider_id.strip():
        raise InvalidProviderDataError("share count missing provider_id provenance")
    if not snapshot.provenance.provider_name.strip():
        raise InvalidProviderDataError("share count missing provider_name provenance")
    if snapshot.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={snapshot.provenance.source_type!r}"
        )
    if snapshot.unit != ShareCountUnit.SHARES:
        raise InvalidProviderDataError(
            "share count unit must be shares (not currency, percent, or other)"
        )
    if not isinstance(snapshot.basis, ShareCountBasis):
        raise InvalidProviderDataError(
            "share count basis is not a known semantic basis"
        )

    shares = snapshot.shares
    if not isinstance(shares, ShareCountField):
        raise InvalidProviderDataError("share count field missing")
    if shares.available and shares.value is None:
        raise InvalidProviderDataError("share count marked available with null value")
    if not shares.available and shares.value is not None:
        raise InvalidProviderDataError("share count has value but marked unavailable")
    if not shares.available:
        return
    assert shares.value is not None
    if not shares.value.is_finite():
        raise InvalidProviderDataError("share count must be finite")
    if shares.value <= 0:
        raise InvalidProviderDataError("share count must be > 0")


def assert_share_count_identity(
    snapshot: ShareCountSnapshot,
    *,
    symbol: str,
    exchange: str | None = None,
    isin: str | None = None,
) -> None:
    """Fail closed when populated identity fields disagree.

    Unpopulated fields on either side are not a mismatch.
    """
    requested_symbol = _normalize_identity(symbol)
    snapshot_symbol = _normalize_identity(snapshot.symbol)
    if not requested_symbol or snapshot_symbol != requested_symbol:
        raise InvalidProviderDataError(
            "share-count identity mismatch: "
            f"requested {requested_symbol or 'unknown'}, "
            f"got {snapshot_symbol or 'unknown'}"
        )

    requested_exchange = _normalize_identity(exchange)
    snapshot_exchange = _normalize_identity(snapshot.exchange)
    if (
        requested_exchange
        and snapshot_exchange
        and requested_exchange != snapshot_exchange
    ):
        raise InvalidProviderDataError(
            "share-count exchange mismatch: "
            f"requested {requested_exchange}, got {snapshot_exchange}"
        )

    requested_isin = _normalize_identity(isin)
    snapshot_isin = _normalize_identity(snapshot.isin)
    if requested_isin and snapshot_isin and requested_isin != snapshot_isin:
        raise InvalidProviderDataError(
            "share-count ISIN mismatch: "
            f"requested {requested_isin}, got {snapshot_isin}"
        )
