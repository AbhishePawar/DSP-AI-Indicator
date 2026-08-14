"""AI Research Copilot models (EPIC-A001).

Grounded answers from R001/R002/R004/R005 only — never fabricate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "COPILOT_SCHEMA_VERSION",
    "COPILOT_SERVICE_VERSION",
    "UNAVAILABLE_MESSAGE",
    "Citation",
    "CopilotResponse",
    "ProcessedQuestion",
    "ResearchContextBundle",
    "freeze_mapping",
    "utc_now",
]

COPILOT_SCHEMA_VERSION = "1.0.0"
COPILOT_SERVICE_VERSION = "1.0.0"


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ProcessedQuestion:
    raw: str
    normalized: str
    topics: tuple[str, ...]
    intent: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw": self.raw,
            "normalized": self.normalized,
            "topics": list(self.topics),
            "intent": self.intent,
        }


@dataclass(frozen=True, slots=True)
class Citation:
    source_kind: str  # research_object | institutional_report | archive_snapshot | research_diff
    section: str
    path: str
    available: bool
    label: str
    research_object_id: str | None = None
    report_id: str | None = None
    snapshot_id: str | None = None
    diff_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_kind": self.source_kind,
            "section": self.section,
            "path": self.path,
            "available": self.available,
            "label": self.label,
            "research_object_id": self.research_object_id,
            "report_id": self.report_id,
            "snapshot_id": self.snapshot_id,
            "diff_id": self.diff_id,
        }


@dataclass(frozen=True, slots=True)
class ResearchContextBundle:
    """Deterministic assembled context — read-only views of platform outputs."""

    research_object: Mapping[str, Any] | None
    report: Mapping[str, Any] | None
    archive_snapshot: Mapping[str, Any] | None
    research_diff: Mapping[str, Any] | None
    assembled_at: str
    source_refs: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "assembled_at": self.assembled_at,
            "source_refs": _plain(self.source_refs),
            "has_research_object": self.research_object is not None,
            "has_report": self.report is not None,
            "has_archive_snapshot": self.archive_snapshot is not None,
            "has_research_diff": self.research_diff is not None,
            "research_object": _plain(self.research_object)
            if self.research_object is not None
            else None,
            "report": _plain(self.report) if self.report is not None else None,
            "archive_snapshot": _plain(self.archive_snapshot)
            if self.archive_snapshot is not None
            else None,
            "research_diff": _plain(self.research_diff)
            if self.research_diff is not None
            else None,
        }


@dataclass(frozen=True, slots=True)
class CopilotResponse:
    response_id: str
    schema_version: str
    service_version: str
    created_at: str
    conversation_id: str | None
    question: Mapping[str, Any]
    answer: str
    citations: tuple[Citation, ...]
    unavailable: bool
    prompt: Mapping[str, Any]
    context_refs: Mapping[str, Any]
    provenance: Mapping[str, Any]
    audit: Mapping[str, Any]
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "response_id": self.response_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "conversation_id": self.conversation_id,
            "question": _plain(self.question),
            "answer": self.answer,
            "citations": [c.to_dict() for c in self.citations],
            "unavailable": self.unavailable,
            "prompt": _plain(self.prompt),
            "context_refs": _plain(self.context_refs),
            "provenance": _plain(self.provenance),
            "audit": _plain(self.audit),
            "limitations": list(self.limitations),
        }
