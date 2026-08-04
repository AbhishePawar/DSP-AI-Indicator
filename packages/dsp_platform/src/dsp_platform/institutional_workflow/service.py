"""Institutional Workflow & Approval service (EPIC-A007)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.institutional_workflow.citations import build_workflow_citations
from dsp_platform.institutional_workflow.models import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STAGES,
    UNAVAILABLE_MESSAGE,
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_SERVICE_VERSION,
    ApprovalRecord,
    CommentRecord,
    DecisionEvent,
    ReviewerRecord,
    WorkflowInstance,
    WorkflowResult,
    freeze_mapping,
    utc_now,
)
from dsp_platform.institutional_workflow.registry import get_workflow_registry
from dsp_platform.institutional_workflow.serde import workflow_result_to_dict
from dsp_platform.institutional_workflow.templates import (
    DEFAULT_TEMPLATE_ID,
    get_workflow_template,
)
from dsp_platform.institutional_workflow.validation import (
    InstitutionalWorkflowValidationError,
    validate_workflow_result,
)

__all__ = [
    "WORKFLOW_SERVICE_VERSION",
    "WorkflowService",
    "apply_workflow_action",
]


def _audit_event(
    *,
    event: str,
    workflow_id: str,
    stage: str,
    actor_id: str | None = None,
    detail: Mapping[str, Any] | None = None,
    created_at: str,
) -> Mapping[str, Any]:
    row: dict[str, Any] = {
        "event": event,
        "workflow_id": workflow_id,
        "stage": stage,
        "created_at": created_at,
    }
    if actor_id:
        row["actor_id"] = actor_id
    if detail:
        row["detail"] = dict(detail)
    return freeze_mapping(row) or freeze_mapping({})


def _normalize_refs(refs: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not refs:
        return freeze_mapping({}) or freeze_mapping({})
    cleaned: dict[str, Any] = {}
    for key in sorted(refs.keys()):
        value = refs.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            cleaned[str(key)] = text
    return freeze_mapping(cleaned) or freeze_mapping({})


def _wrap_result(
    *,
    action: str,
    workflow: WorkflowInstance,
    result_id: str | None,
    created_at: str | None,
) -> WorkflowResult:
    created = created_at or utc_now().isoformat()
    rid = result_id or str(uuid.uuid4())
    citations = build_workflow_citations(
        workflow.artifact_refs, workflow_id=workflow.workflow_id
    )
    provenance = {
        "source": "institutional_workflow",
        "service_version": WORKFLOW_SERVICE_VERSION,
        "providers_called": False,
        "engines_called": False,
        "calculations_performed": False,
        "research_mutated": False,
        "template_id": workflow.template_id,
        "workflow_id": workflow.workflow_id,
    }
    audit = {
        "result_id": rid,
        "created_at": created,
        "action": action,
        "workflow_id": workflow.workflow_id,
        "stage": workflow.stage,
        "decision_count": len(workflow.decision_history),
        "approval_count": len(workflow.approvals),
        "comment_count": len(workflow.comments),
        "citation_count": len(citations),
    }
    limitations = (
        "Manages workflow state only — research artifacts are never modified.",
        "No valuation, scoring, optimisation, or recommendations.",
        "No providers or engines executed.",
    )
    result = WorkflowResult(
        result_id=rid,
        schema_version=WORKFLOW_SCHEMA_VERSION,
        service_version=WORKFLOW_SERVICE_VERSION,
        created_at=created,
        action=action,
        workflow=freeze_mapping(workflow.to_dict()) or freeze_mapping({}),
        citations=citations,
        provenance=freeze_mapping(provenance) or freeze_mapping({}),
        audit=freeze_mapping(audit) or freeze_mapping({}),
        limitations=limitations,
    )
    validate_workflow_result(result)
    return result


class WorkflowService:
    """Deterministic institutional research lifecycle manager."""

    def create(
        self,
        *,
        subject: str,
        template_id: str | None = None,
        artifact_refs: Mapping[str, Any] | None = None,
        reviewers: list[Mapping[str, Any]] | None = None,
        workflow_id: str | None = None,
        actor_id: str | None = None,
        created_at: str | None = None,
        result_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkflowResult:
        subject_norm = str(subject or "").strip()
        if not subject_norm:
            raise InstitutionalWorkflowValidationError("subject is required")
        subject_norm = subject_norm.upper()
        template = get_workflow_template(template_id)
        created = created_at or utc_now().isoformat()
        wid = workflow_id or str(uuid.uuid4())
        actor = actor_id or "system"

        reviewer_rows: list[ReviewerRecord] = []
        for row in reviewers or []:
            if not isinstance(row, Mapping):
                continue
            rid = str(row.get("reviewer_id") or "").strip()
            role = str(row.get("role") or "reviewer").strip()
            if not rid:
                continue
            reviewer_rows.append(
                ReviewerRecord(
                    reviewer_id=rid,
                    role=role,
                    display_name=row.get("display_name"),
                )
            )
        reviewer_rows.sort(key=lambda r: (r.role, r.reviewer_id))

        audit = (
            _audit_event(
                event="workflow_created",
                workflow_id=wid,
                stage="draft",
                actor_id=actor,
                detail={"template_id": template["template_id"]},
                created_at=created,
            ),
        )
        workflow = WorkflowInstance(
            workflow_id=wid,
            template_id=str(template["template_id"]),
            subject=subject_norm,
            stage="draft",
            created_at=created,
            updated_at=created,
            artifact_refs=_normalize_refs(artifact_refs),
            reviewers=tuple(reviewer_rows),
            comments=(),
            approvals=(),
            decision_history=(),
            audit_trail=audit,
            metadata=freeze_mapping(dict(metadata or {})) or freeze_mapping({}),
        )
        get_workflow_registry().put(workflow)
        return _wrap_result(
            action="create",
            workflow=workflow,
            result_id=result_id,
            created_at=created,
        )

    def transition(
        self,
        *,
        workflow_id: str,
        to_stage: str,
        actor_id: str,
        reason: str | None = None,
        note: str | None = None,
        created_at: str | None = None,
        result_id: str | None = None,
        approval_id: str | None = None,
        event_id: str | None = None,
    ) -> WorkflowResult:
        registry = get_workflow_registry()
        try:
            current = registry.require(workflow_id)
        except KeyError as exc:
            raise InstitutionalWorkflowValidationError(str(exc)) from exc

        target = str(to_stage or "").strip().lower()
        if target not in ALLOWED_TRANSITIONS:
            raise InstitutionalWorkflowValidationError(f"invalid stage {target!r}")
        if current.stage in TERMINAL_STAGES:
            raise InstitutionalWorkflowValidationError(
                f"workflow is terminal at stage {current.stage!r}"
            )
        allowed = ALLOWED_TRANSITIONS.get(current.stage, ())
        if target not in allowed:
            raise InstitutionalWorkflowValidationError(
                f"transition {current.stage!r} -> {target!r} not allowed"
            )

        created = created_at or utc_now().isoformat()
        actor = str(actor_id or "").strip() or "system"
        decision = (
            "reject"
            if target == "rejected"
            else ("approve" if target in {"approved", "published"} else "advance")
        )
        approval = ApprovalRecord(
            approval_id=approval_id or str(uuid.uuid4()),
            stage=current.stage,
            decision=decision,
            reviewer_id=actor,
            created_at=created,
            note=note,
        )
        event = DecisionEvent(
            event_id=event_id or str(uuid.uuid4()),
            from_stage=current.stage,
            to_stage=target,
            actor_id=actor,
            created_at=created,
            reason=reason,
        )
        audit_event = _audit_event(
            event="stage_transition",
            workflow_id=current.workflow_id,
            stage=target,
            actor_id=actor,
            detail={
                "from_stage": current.stage,
                "to_stage": target,
                "reason": reason,
            },
            created_at=created,
        )
        updated = WorkflowInstance(
            workflow_id=current.workflow_id,
            template_id=current.template_id,
            subject=current.subject,
            stage=target,
            created_at=current.created_at,
            updated_at=created,
            artifact_refs=current.artifact_refs,
            reviewers=current.reviewers,
            comments=current.comments,
            approvals=tuple(
                sorted(
                    (*current.approvals, approval),
                    key=lambda a: (a.created_at, a.approval_id),
                )
            ),
            decision_history=tuple(
                sorted(
                    (*current.decision_history, event),
                    key=lambda d: (d.created_at, d.event_id),
                )
            ),
            audit_trail=tuple((*current.audit_trail, audit_event)),
            metadata=current.metadata,
        )
        registry.put(updated)
        return _wrap_result(
            action="transition",
            workflow=updated,
            result_id=result_id,
            created_at=created,
        )

    def add_comment(
        self,
        *,
        workflow_id: str,
        author_id: str,
        body: str,
        created_at: str | None = None,
        result_id: str | None = None,
        comment_id: str | None = None,
    ) -> WorkflowResult:
        registry = get_workflow_registry()
        try:
            current = registry.require(workflow_id)
        except KeyError as exc:
            raise InstitutionalWorkflowValidationError(str(exc)) from exc
        text = str(body or "").strip()
        if not text:
            raise InstitutionalWorkflowValidationError("comment body is required")
        created = created_at or utc_now().isoformat()
        author = str(author_id or "").strip() or "system"
        comment = CommentRecord(
            comment_id=comment_id or str(uuid.uuid4()),
            author_id=author,
            stage=current.stage,
            body=text,
            created_at=created,
        )
        audit_event = _audit_event(
            event="comment_added",
            workflow_id=current.workflow_id,
            stage=current.stage,
            actor_id=author,
            detail={"comment_id": comment.comment_id},
            created_at=created,
        )
        updated = WorkflowInstance(
            workflow_id=current.workflow_id,
            template_id=current.template_id,
            subject=current.subject,
            stage=current.stage,
            created_at=current.created_at,
            updated_at=created,
            artifact_refs=current.artifact_refs,
            reviewers=current.reviewers,
            comments=tuple(
                sorted(
                    (*current.comments, comment),
                    key=lambda c: (c.created_at, c.comment_id),
                )
            ),
            approvals=current.approvals,
            decision_history=current.decision_history,
            audit_trail=tuple((*current.audit_trail, audit_event)),
            metadata=current.metadata,
        )
        registry.put(updated)
        return _wrap_result(
            action="comment",
            workflow=updated,
            result_id=result_id,
            created_at=created,
        )

    def get(
        self,
        *,
        workflow_id: str,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> WorkflowResult:
        registry = get_workflow_registry()
        try:
            current = registry.require(workflow_id)
        except KeyError as exc:
            raise InstitutionalWorkflowValidationError(
                f"{exc}; {UNAVAILABLE_MESSAGE}"
            ) from exc
        return _wrap_result(
            action="get",
            workflow=current,
            result_id=result_id,
            created_at=created_at or current.updated_at,
        )

    def assign_reviewer(
        self,
        *,
        workflow_id: str,
        reviewer_id: str,
        role: str = "reviewer",
        display_name: str | None = None,
        actor_id: str | None = None,
        created_at: str | None = None,
        result_id: str | None = None,
    ) -> WorkflowResult:
        registry = get_workflow_registry()
        try:
            current = registry.require(workflow_id)
        except KeyError as exc:
            raise InstitutionalWorkflowValidationError(
                f"{exc}; {UNAVAILABLE_MESSAGE}"
            ) from exc
        rid = str(reviewer_id or "").strip()
        if not rid:
            raise InstitutionalWorkflowValidationError("reviewer_id is required")
        role_n = str(role or "reviewer").strip().lower() or "reviewer"
        if any(r.reviewer_id == rid for r in current.reviewers):
            raise InstitutionalWorkflowValidationError(
                f"duplicate reviewer assignment {rid!r}"
            )
        created = created_at or utc_now().isoformat()
        actor = str(actor_id or "").strip() or "system"
        reviewer = ReviewerRecord(
            reviewer_id=rid,
            role=role_n,
            display_name=display_name,
        )
        audit_event = _audit_event(
            event="reviewer_assigned",
            workflow_id=current.workflow_id,
            stage=current.stage,
            actor_id=actor,
            detail={"reviewer_id": rid, "role": role_n},
            created_at=created,
        )
        reviewers = tuple(
            sorted(
                (*current.reviewers, reviewer),
                key=lambda r: (r.role, r.reviewer_id),
            )
        )
        updated = WorkflowInstance(
            workflow_id=current.workflow_id,
            template_id=current.template_id,
            subject=current.subject,
            stage=current.stage,
            created_at=current.created_at,
            updated_at=created,
            artifact_refs=current.artifact_refs,
            reviewers=reviewers,
            comments=current.comments,
            approvals=current.approvals,
            decision_history=current.decision_history,
            audit_trail=tuple((*current.audit_trail, audit_event)),
            metadata=current.metadata,
        )
        registry.put(updated)
        return _wrap_result(
            action="assign_reviewer",
            workflow=updated,
            result_id=result_id,
            created_at=created,
        )

    def history(
        self,
        *,
        workflow_id: str,
        result_id: str | None = None,
        created_at: str | None = None,
    ) -> WorkflowResult:
        """Return workflow with decision history / approvals / audit emphasized."""
        result = self.get(
            workflow_id=workflow_id,
            result_id=result_id,
            created_at=created_at,
        )
        # Re-wrap with action=history for audit clarity
        return WorkflowResult(
            result_id=result.result_id,
            schema_version=result.schema_version,
            service_version=result.service_version,
            created_at=result.created_at,
            action="history",
            workflow=result.workflow,
            citations=result.citations,
            provenance=result.provenance,
            audit=freeze_mapping(
                {
                    **dict(result.audit),
                    "action": "history",
                    "decision_count": len(
                        result.workflow.get("decision_history") or []
                    ),
                    "approval_count": len(result.workflow.get("approvals") or []),
                    "comment_count": len(result.workflow.get("comments") or []),
                }
            )
            or freeze_mapping({}),
            limitations=result.limitations,
        )


def apply_workflow_action(
    *,
    action: str,
    **kwargs: Any,
) -> dict[str, Any]:
    service = WorkflowService()
    act = str(action or "").strip().lower()
    if act == "create":
        result = service.create(**kwargs)
    elif act == "transition":
        result = service.transition(**kwargs)
    elif act in {"approve", "reject"}:
        # Convenience: map to transition targets without inventing research
        target = "approved" if act == "approve" else "rejected"
        # From committee_review → approved/rejected; from review/compliance → rejected only
        # Caller may pass to_stage override; default uses convenience target when legal
        to_stage = kwargs.pop("to_stage", None) or target
        result = service.transition(**kwargs, to_stage=to_stage)
    elif act == "comment":
        result = service.add_comment(**kwargs)
    elif act == "assign_reviewer":
        result = service.assign_reviewer(**kwargs)
    elif act == "history":
        result = service.history(**kwargs)
    elif act == "get":
        result = service.get(**kwargs)
    else:
        raise InstitutionalWorkflowValidationError(f"unknown action {action!r}")
    return workflow_result_to_dict(result)
