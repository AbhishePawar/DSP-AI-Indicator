"""Validate authenticated ownership bundles — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.exceptions import InvalidProviderDataError
from data_engine.ownership.models import (
    OWNERSHIP_HOLDER_TYPES,
    AuthenticatedOwnership,
    OwnershipStake,
)
from data_engine.connector_framework.models import ConnectorField

__all__ = ["validate_authenticated_ownership"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _check_field(name: str, f: ConnectorField) -> None:
    if f.available and f.value is None:
        raise InvalidProviderDataError(f"ownership field '{name}' marked available with null value")
    if not f.available and f.value is not None:
        raise InvalidProviderDataError(f"ownership field '{name}' has value but marked unavailable")


def _validate_stake(stake: OwnershipStake, index: int) -> None:
    prefix = f"stakes[{index}]"
    if stake.holder_type not in OWNERSHIP_HOLDER_TYPES:
        raise InvalidProviderDataError(
            f"{prefix}.holder_type must be one of {sorted(OWNERSHIP_HOLDER_TYPES)}, "
            f"got {stake.holder_type!r}"
        )
    _check_field(f"{prefix}.percent_held", stake.percent_held)
    _check_field(f"{prefix}.shares_held", stake.shares_held)
    if stake.percent_held.available and stake.percent_held.value is not None:
        pct = float(stake.percent_held.value)
        if pct < 0 or pct > 100:
            raise InvalidProviderDataError(f"{prefix}.percent_held out of range: {pct}")


def validate_authenticated_ownership(bundle: AuthenticatedOwnership) -> None:
    """Reject structurally invalid ownership bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("ownership bundle missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("ownership bundle missing provider_id provenance")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("ownership bundle missing provider_name provenance")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    for name in (
        "promoter_holding_percent",
        "institutional_holding_percent",
        "public_holding_percent",
    ):
        _check_field(name, getattr(bundle, name))
    if not bundle.stakes:
        raise InvalidProviderDataError(
            "authenticated ownership must include at least one stake "
            "(use None from adapter when unavailable)"
        )
    for i, stake in enumerate(bundle.stakes):
        _validate_stake(stake, i)
