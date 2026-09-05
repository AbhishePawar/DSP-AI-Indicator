"""Production current-outstanding protocol models.

AI output remains an untrusted candidate. Only DSP acceptance may create
a ShareCountSnapshot. This module does not calculate valuation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Any

from data_engine import ShareCountSnapshot

__all__ = [
    "CurrentOutstandingDiagnostic",
    "CurrentOutstandingProtocolResult",
    "PROTOCOL_SCHEMA_VERSION",
    "UntrustedShareCountAiCandidate",
]

PROTOCOL_SCHEMA_VERSION = "dsp.current_outstanding_protocol.v1"


class CurrentOutstandingDiagnostic(StrEnum):
    UPSTOX_VALUE_PRESENT = "UPSTOX_VALUE_PRESENT"
    UPSTOX_VALUE_UNAVAILABLE = "UPSTOX_VALUE_UNAVAILABLE"
    EVIDENCE_DISCOVERY_BLOCKED = "EVIDENCE_DISCOVERY_BLOCKED"
    DOCUMENT_RETRIEVAL_BLOCKED = "DOCUMENT_RETRIEVAL_BLOCKED"
    AI_EXECUTION_BLOCKED = "AI_EXECUTION_BLOCKED"
    AI_CANDIDATE_REJECTED = "AI_CANDIDATE_REJECTED"
    SHARECOUNT_VALIDATED = "SHARECOUNT_VALIDATED"
    SHARECOUNT_CONFLICT = "SHARECOUNT_CONFLICT"
    SHARECOUNT_UNAVAILABLE = "SHARECOUNT_UNAVAILABLE"
    OPTION_B_UNPROVEN = "OPTION_B_UNPROVEN"


@dataclass(frozen=True, slots=True)
class UntrustedShareCountAiCandidate:
    """AI-extracted claim. Not evidence authority and not a snapshot."""

    company_identity: str
    claimed_share_count: object
    unit: str
    as_of_date: date | str | None
    source_reference: str
    evidence_reference: str
    supporting_excerpt: str
    validation_status: str = "untrusted"
    ticker: str = ""
    exchange: str = ""
    isin: str = ""
    mic: str = ""
    source_name: str = ""
    source_type: str = ""
    explanation: str = ""
    claim_type: str = "CURRENT_OUTSTANDING"

    def to_dict(self) -> dict[str, Any]:
        as_of = self.as_of_date
        return {
            "company_identity": self.company_identity,
            "ticker": self.ticker,
            "exchange": self.exchange,
            "isin": self.isin,
            "mic": self.mic,
            "claimed_share_count": self.claimed_share_count,
            "unit": self.unit,
            "as_of_date": as_of.isoformat() if isinstance(as_of, date) else as_of,
            "source_name": self.source_name,
            "source_reference": self.source_reference,
            "source_type": self.source_type,
            "evidence_reference": self.evidence_reference,
            "supporting_excerpt": self.supporting_excerpt,
            "explanation": self.explanation,
            "claim_type": self.claim_type,
            "validation_status": self.validation_status,
            "trusted": False,
            "may_create_snapshot": False,
        }


@dataclass(frozen=True, slots=True)
class CurrentOutstandingProtocolResult:
    """Server-internal protocol outcome. Serialize via ``to_public_dict``."""

    diagnostic: CurrentOutstandingDiagnostic
    snapshot: ShareCountSnapshot | None
    current_shares_outstanding: float | None
    upstox_status: CurrentOutstandingDiagnostic
    untrusted_candidate: UntrustedShareCountAiCandidate | None = None
    detail: str | None = None
    schema_version: str = PROTOCOL_SCHEMA_VERSION

    def to_public_dict(self) -> dict[str, Any]:
        """Client-safe view. Never includes prompts, routing, or AI prose."""
        shares = self.current_shares_outstanding
        return {
            "schema_version": self.schema_version,
            "diagnostic": self.diagnostic.value,
            "upstox_status": self.upstox_status.value,
            "current_shares_outstanding": shares,
            "share_count_available": self.snapshot is not None and shares is not None,
        }
