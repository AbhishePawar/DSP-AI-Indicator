"""Authenticated regulatory/corporate filings models.

Retrieval and normalization only — no document parsing or summarization
happens here (that remains the job of the existing research/copilot
engines, which may consume ``Filing.url`` as an input).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorProvenance,
)

__all__ = [
    "FILING_TYPES",
    "AuthenticatedFilings",
    "Filing",
]

FILING_TYPES = frozenset(
    {
        "10-K",
        "10-Q",
        "8-K",
        "annual_report",
        "quarterly_report",
        "investor_presentation",
        "conference_call_transcript",
        "prospectus",
        "corporate_announcement",
        "shareholding_pattern",
        "other",
    }
)


@dataclass(frozen=True, slots=True)
class Filing:
    """One authenticated filing/disclosure — as-reported fields only."""

    filing_id: str
    filing_type: str
    title: str
    url: str
    filed_at: date
    period_of_report: date | None = None
    accession_number: str | None = None
    source: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "filing_id": self.filing_id,
            "filing_type": self.filing_type,
            "title": self.title,
            "url": self.url,
            "filed_at": self.filed_at.isoformat(),
            "period_of_report": self.period_of_report.isoformat()
            if self.period_of_report
            else None,
            "accession_number": self.accession_number,
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedFilings:
    """Authenticated filings bundle for one company."""

    identity: ConnectorCompanyIdentity
    filings: tuple[Filing, ...]
    provenance: ConnectorProvenance

    def has_any_filing(self) -> bool:
        return len(self.filings) > 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "filings": [f.to_public_dict() for f in self.filings],
            "provenance": self.provenance.to_dict(),
        }
