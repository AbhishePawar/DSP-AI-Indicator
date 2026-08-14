"""Collaboration architecture ports only — no realtime implementation (EPS-002 Phase E).

Documents and reserves models/ports for shared research, comments, mentions,
approvals, review workflows, committee approval, and ownership transfer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from enterprise.models import freeze_mapping, utc_now

__all__ = [
    "COLLABORATION_ARCHITECTURE",
    "ApprovalRequest",
    "CollaborationPort",
    "Comment",
    "NullCollaborationAdapter",
    "SharedResearchRef",
]


COLLABORATION_ARCHITECTURE: dict[str, Any] = {
    "status": "architecture_only",
    "realtime": False,
    "capabilities_reserved": [
        "shared_research",
        "comments",
        "mentions",
        "approvals",
        "review_workflows",
        "committee_approval",
        "ownership_transfer",
    ],
    "notes": [
        "Ports and models prepared for institutional collaboration.",
        "Realtime transport (WebSocket/SSE) is intentionally not implemented.",
        "Research engines and canvas collaboration demos remain separate.",
    ],
}


@dataclass(frozen=True, slots=True)
class SharedResearchRef:
    share_id: str
    org_id: str
    research_ref: str
    owner_user_id: str
    visibility: str
    created_at: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "share_id": self.share_id,
            "org_id": self.org_id,
            "research_ref": self.research_ref,
            "owner_user_id": self.owner_user_id,
            "visibility": self.visibility,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class Comment:
    comment_id: str
    org_id: str
    target_ref: str
    author_user_id: str
    body: str
    created_at: str
    mentions: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "comment_id": self.comment_id,
            "org_id": self.org_id,
            "target_ref": self.target_ref,
            "author_user_id": self.author_user_id,
            "body": self.body,
            "created_at": self.created_at,
            "mentions": list(self.mentions),
        }


@dataclass(frozen=True, slots=True)
class ApprovalRequest:
    approval_id: str
    org_id: str
    target_ref: str
    requested_by: str
    status: str
    created_at: str
    committee_required: bool = False
    approver_user_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "org_id": self.org_id,
            "target_ref": self.target_ref,
            "requested_by": self.requested_by,
            "status": self.status,
            "created_at": self.created_at,
            "committee_required": self.committee_required,
            "approver_user_ids": list(self.approver_user_ids),
        }


@runtime_checkable
class CollaborationPort(Protocol):
    def architecture(self) -> dict[str, Any]: ...

    def list_shared(self, org_id: str) -> list[SharedResearchRef]: ...

    def list_comments(self, org_id: str, target_ref: str) -> list[Comment]: ...

    def list_approvals(self, org_id: str) -> list[ApprovalRequest]: ...


class NullCollaborationAdapter:
    """Architecture-only adapter — returns empty collections, no realtime."""

    def architecture(self) -> dict[str, Any]:
        return dict(COLLABORATION_ARCHITECTURE)

    def list_shared(self, org_id: str) -> list[SharedResearchRef]:
        return []

    def list_comments(self, org_id: str, target_ref: str) -> list[Comment]:
        return []

    def list_approvals(self, org_id: str) -> list[ApprovalRequest]:
        return []


def collaboration_blueprint() -> dict[str, Any]:
    """Static architecture document for ops/admin surfaces."""
    return {
        **COLLABORATION_ARCHITECTURE,
        "models": [
            "SharedResearchRef",
            "Comment",
            "ApprovalRequest",
        ],
        "ports": ["CollaborationPort"],
        "generated_at": utc_now().isoformat(),
        "freeze_example": dict(freeze_mapping({"realtime": False})),
    }
