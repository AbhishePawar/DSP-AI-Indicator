"""Validate authenticated insider trading bundles — reject invalid / fabricated envelopes."""

from __future__ import annotations

from data_engine.connector_framework.models import ConnectorField
from data_engine.exceptions import InvalidProviderDataError
from data_engine.insider_trading.models import (
    INSIDER_TRANSACTION_TYPES,
    AuthenticatedInsiderActivity,
    InsiderTransaction,
)

__all__ = ["validate_authenticated_insider_activity"]

_DISALLOWED_SOURCE = frozenset(
    {"", "example", "dummy", "placeholder", "fabricated", "estimated"}
)


def _check_field(name: str, f: ConnectorField) -> None:
    if f.available and f.value is None:
        raise InvalidProviderDataError(f"insider field '{name}' marked available with null value")
    if not f.available and f.value is not None:
        raise InvalidProviderDataError(f"insider field '{name}' has value but marked unavailable")


def _validate_transaction(txn: InsiderTransaction, index: int) -> None:
    prefix = f"transactions[{index}]"
    if not txn.transaction_id or not str(txn.transaction_id).strip():
        raise InvalidProviderDataError(f"{prefix} missing transaction_id")
    if not txn.insider_name or not str(txn.insider_name).strip():
        raise InvalidProviderDataError(f"{prefix} missing insider_name")
    if txn.transaction_type not in INSIDER_TRANSACTION_TYPES:
        raise InvalidProviderDataError(
            f"{prefix}.transaction_type must be one of {sorted(INSIDER_TRANSACTION_TYPES)}, "
            f"got {txn.transaction_type!r}"
        )
    for name in ("shares", "price", "value"):
        _check_field(f"{prefix}.{name}", getattr(txn, name))


def validate_authenticated_insider_activity(bundle: AuthenticatedInsiderActivity) -> None:
    """Reject structurally invalid insider bundles. Never invent replacements."""
    if not bundle.identity.symbol or not str(bundle.identity.symbol).strip():
        raise InvalidProviderDataError("insider activity missing identity.symbol")
    if not bundle.provenance.provider_id.strip():
        raise InvalidProviderDataError("insider activity missing provider_id provenance")
    if not bundle.provenance.provider_name.strip():
        raise InvalidProviderDataError("insider activity missing provider_name provenance")
    if bundle.provenance.source_type.strip().lower() in _DISALLOWED_SOURCE:
        raise InvalidProviderDataError(
            f"disallowed provenance source_type={bundle.provenance.source_type!r}"
        )
    if not bundle.transactions:
        raise InvalidProviderDataError(
            "authenticated insider activity must include at least one transaction "
            "(use None from adapter when unavailable)"
        )
    for i, txn in enumerate(bundle.transactions):
        _validate_transaction(txn, i)
