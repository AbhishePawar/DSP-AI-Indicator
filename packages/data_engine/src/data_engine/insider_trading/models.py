"""Authenticated insider trading models.

Retrieval and normalization only — as-reported transactions, never
derived signals (no "cluster buying" scoring, no sentiment).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
)

__all__ = [
    "INSIDER_TRANSACTION_TYPES",
    "AuthenticatedInsiderActivity",
    "InsiderTransaction",
]

INSIDER_TRANSACTION_TYPES = frozenset(
    {"buy", "sell", "grant", "exercise", "gift", "pledge", "release_pledge", "other"}
)


@dataclass(frozen=True, slots=True)
class InsiderTransaction:
    """One authenticated insider transaction — as-reported fields only."""

    transaction_id: str
    insider_name: str
    role: str | None
    transaction_type: str
    shares: ConnectorField
    price: ConnectorField
    value: ConnectorField
    transaction_date: date
    filed_at: date | None = None
    source: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "insider_name": self.insider_name,
            "role": self.role,
            "transaction_type": self.transaction_type,
            "shares": self.shares.to_float(),
            "price": self.price.to_float(),
            "value": self.value.to_float(),
            "transaction_date": self.transaction_date.isoformat(),
            "filed_at": self.filed_at.isoformat() if self.filed_at else None,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedInsiderActivity:
    """Authenticated insider trading bundle for one company."""

    identity: ConnectorCompanyIdentity
    transactions: tuple[InsiderTransaction, ...]
    provenance: ConnectorProvenance

    def has_any_transaction(self) -> bool:
        return len(self.transactions) > 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "transactions": [t.to_public_dict() for t in self.transactions],
            "provenance": self.provenance.to_dict(),
        }
