"""Institutional Multi-Agent Investment Committee models (EPIC-A005)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "AGENT_IDS",
    "COMMITTEE_SCHEMA_VERSION",
    "COMMITTEE_SERVICE_VERSION",
    "CONFIDENCE_LEVELS",
    "STANCES",
    "UNAVAILABLE_MESSAGE",
    "AgentReview",
    "CommitteeReport",
    "CommitteeContext",
    "freeze_mapping",
    "utc_now",
]

COMMITTEE_SCHEMA_VERSION = "1.0.0"
COMMITTEE_SERVICE_VERSION = "1.0.0"

# Deterministic agent order
AGENT_IDS = (
    "buffett",
    "graham",
    "lynch",
    "quality",
    "risk",
    "governance",
    "valuation",
    "devils_advocate",
)

STANCES = (
    "supportive",  # focus evidence present and usable
    "cautionary",  # gaps, risks, or conflicts cited from artifacts
    "unavailable",  # no usable evidence for this lens
)

CONFIDENCE_LEVELS = ("high", "medium", "low", "unavailable")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class CommitteeContext:
    """Read-only distributed context — excerpts only, no mutation."""

    subject: str
    research_object: Mapping[str, Any] | None
    report: Mapping[str, Any] | None
    snapshots: tuple[Mapping[str, Any], ...]
    diffs: tuple[Mapping[str, Any], ...]
    copilot_response: Mapping[str, Any] | None
    portfolio_intelligence: Mapping[str, Any] | None
    monitoring_result: Mapping[str, Any] | None
    workspace: Mapping[str, Any] | None
    section_index: Mapping[str, Any]
    source_flags: Mapping[str, bool]

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "subject": self.subject,
            "source_flags": _plain(self.source_flags),
            "section_index": _plain(self.section_index),
            "snapshot_count": len(self.snapshots),
            "diff_count": len(self.diffs),
            "has_research_object": self.research_object is not None,
            "has_report": self.report is not None,
            "has_copilot": self.copilot_response is not None,
            "has_portfolio": self.portfolio_intelligence is not None,
            "has_monitoring": self.monitoring_result is not None,
            "has_workspace": self.workspace is not None,
        }


@dataclass(frozen=True, slots=True)
class AgentReview:
    agent_id: str
    agent_name: str
    stance: str
    confidence: str
    summary: str
    findings: tuple[str, ...]
    focus_sections: tuple[str, ...]
    citations: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "stance": self.stance,
            "confidence": self.confidence,
            "summary": self.summary,
            "findings": list(self.findings),
            "focus_sections": list(self.focus_sections),
            "citations": [_plain(c) for c in self.citations],
            "provenance": _plain(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class CommitteeReport:
    report_id: str
    schema_version: str
    service_version: str
    created_at: str
    subject: str
    context: Mapping[str, Any]
    reviews: tuple[AgentReview, ...]
    consensus: Mapping[str, Any]
    minority_opinions: tuple[Mapping[str, Any], ...]
    committee_summary: Mapping[str, Any]
    citations: tuple[Mapping[str, Any], ...]
    provenance: Mapping[str, Any]
    audit: Mapping[str, Any]
    limitations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "report_id": self.report_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "subject": self.subject,
            "context": _plain(self.context),
            "reviews": [r.to_dict() for r in self.reviews],
            "consensus": _plain(self.consensus),
            "minority_opinions": [_plain(m) for m in self.minority_opinions],
            "committee_summary": _plain(self.committee_summary),
            "citations": [_plain(c) for c in self.citations],
            "provenance": _plain(self.provenance),
            "audit": _plain(self.audit),
            "limitations": list(self.limitations),
        }
