"""Provider-neutral external evidence discovery request/result.

Discovery reports candidate sources only. It does not validate truth,
accept share counts, or calculate valuation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from dsp_platform.external_evidence.models import (
    ExternalEvidenceIdentity,
    ExternalEvidenceRecord,
)

__all__ = [
    "DISCOVERY_HANDLING",
    "DISCOVERY_NOT_CONFIGURED",
    "DISCOVERY_SCHEMA_VERSION",
    "MAX_DISCOVERY_EXCERPT_CHARS",
    "ExternalEvidenceDiscoveryRequest",
    "ExternalEvidenceDiscoveryResult",
]

DISCOVERY_SCHEMA_VERSION = "dsp.external_evidence_discovery.v1"
DISCOVERY_NOT_CONFIGURED = "discovery_not_configured"
DISCOVERY_HANDLING = (
    "candidate_discovery_not_validation_not_canonical_acceptance"
)
MAX_DISCOVERY_EXCERPT_CHARS = 500


@dataclass(frozen=True, slots=True)
class ExternalEvidenceDiscoveryRequest:
    """Explicit company-bound discovery request.

    Company name is stored on identity but is never sufficient by itself.
    """

    identity: ExternalEvidenceIdentity
    fact_id: str
    retrieved_at: datetime
    as_of_target: date | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": DISCOVERY_SCHEMA_VERSION,
            "identity": self.identity.to_dict(),
            "fact_id": self.fact_id,
            "retrieved_at": self.retrieved_at.isoformat(),
            "as_of_target": (
                self.as_of_target.isoformat()
                if self.as_of_target is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class ExternalEvidenceDiscoveryResult:
    """Candidate evidence only — not a validated package or DSP port."""

    request: ExternalEvidenceDiscoveryRequest
    records: tuple[ExternalEvidenceRecord, ...]
    schema_version: str = DISCOVERY_SCHEMA_VERSION
    handling: str = DISCOVERY_HANDLING
    discovery_status: str = "candidate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "handling": self.handling,
            "discovery_status": self.discovery_status,
            "request": self.request.to_dict(),
            "record_count": len(self.records),
            "records": [row.to_dict() for row in self.records],
            "may_influence_calculation": False,
            "canonical": False,
        }
