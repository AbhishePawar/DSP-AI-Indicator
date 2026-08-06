"""Authenticated ESG score models.

Retrieval and normalization only — scores are carried through exactly
as reported by the provider; no aggregation or re-weighting happens
here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorField,
    ConnectorProvenance,
)

__all__ = ["CONTROVERSY_LEVELS", "AuthenticatedEsgScore"]

CONTROVERSY_LEVELS = frozenset({"low", "moderate", "significant", "high", "severe"})


@dataclass(frozen=True, slots=True)
class AuthenticatedEsgScore:
    """Authenticated ESG score bundle for one company as of a date."""

    identity: ConnectorCompanyIdentity
    as_of: date | None
    environmental_score: ConnectorField
    social_score: ConnectorField
    governance_score: ConnectorField
    total_score: ConnectorField
    controversy_level: str | None
    provenance: ConnectorProvenance

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "environmental_score": self.environmental_score.to_float(),
            "social_score": self.social_score.to_float(),
            "governance_score": self.governance_score.to_float(),
            "total_score": self.total_score.to_float(),
            "controversy_level": self.controversy_level,
            "provenance": self.provenance.to_dict(),
        }
