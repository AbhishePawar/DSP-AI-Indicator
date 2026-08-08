"""Authenticated shareholding/ownership models.

Retrieval and normalization only — no float/concentration scoring is
computed here; that remains the job of the existing risk engine, which
may consume these fields as an input once available.
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
    "OWNERSHIP_HOLDER_TYPES",
    "AuthenticatedOwnership",
    "OwnershipStake",
]

OWNERSHIP_HOLDER_TYPES = frozenset(
    {
        "promoter",
        "institutional_domestic",
        "institutional_foreign",
        "mutual_fund",
        "insider",
        "retail_public",
        "government",
        "other",
    }
)


@dataclass(frozen=True, slots=True)
class OwnershipStake:
    """One authenticated ownership stake — as-reported fields only."""

    holder_type: str
    holder_name: str | None
    percent_held: ConnectorField
    shares_held: ConnectorField
    metadata: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "holder_type": self.holder_type,
            "holder_name": self.holder_name,
            "percent_held": self.percent_held.to_float(),
            "shares_held": self.shares_held.to_float(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedOwnership:
    """Authenticated shareholding pattern for one company as of a date."""

    identity: ConnectorCompanyIdentity
    as_of: date | None
    stakes: tuple[OwnershipStake, ...]
    promoter_holding_percent: ConnectorField
    institutional_holding_percent: ConnectorField
    public_holding_percent: ConnectorField
    provenance: ConnectorProvenance

    def has_any_stake(self) -> bool:
        return len(self.stakes) > 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "stakes": [s.to_public_dict() for s in self.stakes],
            "promoter_holding_percent": self.promoter_holding_percent.to_float(),
            "institutional_holding_percent": self.institutional_holding_percent.to_float(),
            "public_holding_percent": self.public_holding_percent.to_float(),
            "provenance": self.provenance.to_dict(),
        }
