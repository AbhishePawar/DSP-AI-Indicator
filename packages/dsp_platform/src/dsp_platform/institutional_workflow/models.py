"""Institutional Workflow & Approval models (EPIC-A007)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Mapping

from dsp_platform.research_object.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "ALLOWED_TRANSITIONS",
    "TERMINAL_STAGES",
    "UNAVAILABLE_MESSAGE",
    "WORKFLOW_SCHEMA_VERSION",
    "WORKFLOW_SERVICE_VERSION",
    "WORKFLOW_STAGES",
    "ApprovalRecord",
    "CommentRecord",
    "DecisionEvent",
    "ReviewerRecord",
    "WorkflowInstance",
    "WorkflowResult",
    "freeze_mapping",
    "utc_now",
]

WORKFLOW_SCHEMA_VERSION = "1.0.0"
WORKFLOW_SERVICE_VERSION = "1.0.0"

WORKFLOW_STAGES = (
    "draft",
    "review",
    "compliance_review",
    "committee_review",
    "approved",
    "rejected",
    "published",
)

TERMINAL_STAGES = frozenset({"rejected", "published"})

# Deterministic allowed transitions (workflow state only — not research mutation)
ALLOWED_TRANSITIONS: Mapping[str, tuple[str, ...]] = {
    "draft": ("review",),
    "review": ("compliance_review", "rejected"),
    "compliance_review": ("committee_review", "rejected"),
    "committee_review": ("approved", "rejected"),
    "approved": ("published",),
    "rejected": (),
    "published": (),
}


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class ReviewerRecord:
    reviewer_id: str
    role: str
    display_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer_id": self.reviewer_id,
            "role": self.role,
            "display_name": self.display_name,
        }


@dataclass(frozen=True, slots=True)
class CommentRecord:
    comment_id: str
    author_id: str
    stage: str
    body: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "comment_id": self.comment_id,
            "author_id": self.author_id,
            "stage": self.stage,
            "body": self.body,
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class ApprovalRecord:
    approval_id: str
    stage: str
    decision: str  # approve | reject | advance
    reviewer_id: str
    created_at: str
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "stage": self.stage,
            "decision": self.decision,
            "reviewer_id": self.reviewer_id,
            "created_at": self.created_at,
            "note": self.note,
        }


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    event_id: str
    from_stage: str
    to_stage: str
    actor_id: str
    created_at: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "from_stage": self.from_stage,
            "to_stage": self.to_stage,
            "actor_id": self.actor_id,
            "created_at": self.created_at,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class WorkflowInstance:
    workflow_id: str
    template_id: str
    subject: str
    stage: str
    created_at: str
    updated_at: str
    artifact_refs: Mapping[str, Any]
    reviewers: tuple[ReviewerRecord, ...] = ()
    comments: tuple[CommentRecord, ...] = ()
    approvals: tuple[ApprovalRecord, ...] = ()
    decision_history: tuple[DecisionEvent, ...] = ()
    audit_trail: tuple[Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _plain(obj: Any) -> Any:
            if isinstance(obj, Mapping):
                return {str(k): _plain(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_plain(v) for v in obj]
            return obj

        return {
            "workflow_id": self.workflow_id,
            "template_id": self.template_id,
            "subject": self.subject,
            "stage": self.stage,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "artifact_refs": _plain(self.artifact_refs),
            "reviewers": [r.to_dict() for r in self.reviewers],
            "comments": [c.to_dict() for c in self.comments],
            "approvals": [a.to_dict() for a in self.approvals],
            "decision_history": [d.to_dict() for d in self.decision_history],
            "audit_trail": [_plain(a) for a in self.audit_trail],
            "metadata": _plain(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    result_id: str
    schema_version: str
    service_version: str
    created_at: str
    action: str
    workflow: Mapping[str, Any]
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
            "result_id": self.result_id,
            "schema_version": self.schema_version,
            "service_version": self.service_version,
            "created_at": self.created_at,
            "action": self.action,
            "workflow": _plain(self.workflow),
            "citations": [_plain(c) for c in self.citations],
            "provenance": _plain(self.provenance),
            "audit": _plain(self.audit),
            "limitations": list(self.limitations),
        }
