"""Authenticated earnings call transcript models.

Retrieval and normalization only — no summarization happens here; the
existing research/copilot engines may consume ``content``/``url`` as
an input once available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from data_engine.connector_framework.models import (
    ConnectorCompanyIdentity,
    ConnectorProvenance,
)

__all__ = ["AuthenticatedTranscripts", "EarningsCallTranscript"]


@dataclass(frozen=True, slots=True)
class EarningsCallTranscript:
    """One authenticated earnings call transcript — as-reported fields only."""

    transcript_id: str
    quarter: int | None
    year: int | None
    call_date: date | None
    title: str
    url: str | None = None
    content: str | None = None
    participants: tuple[str, ...] = ()
    source: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "transcript_id": self.transcript_id,
            "quarter": self.quarter,
            "year": self.year,
            "call_date": self.call_date.isoformat() if self.call_date else None,
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "participants": list(self.participants),
            "source": self.source,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class AuthenticatedTranscripts:
    """Authenticated earnings call transcripts bundle for one company."""

    identity: ConnectorCompanyIdentity
    transcripts: tuple[EarningsCallTranscript, ...]
    provenance: ConnectorProvenance

    def has_any_transcript(self) -> bool:
        return len(self.transcripts) > 0

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "authenticated": True,
            "identity": self.identity.to_dict(),
            "transcripts": [t.to_public_dict() for t in self.transcripts],
            "provenance": self.provenance.to_dict(),
        }
