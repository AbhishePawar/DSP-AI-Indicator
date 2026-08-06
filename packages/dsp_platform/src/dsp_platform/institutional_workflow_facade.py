"""Platform façade helpers for Institutional Workflow (EPIC-A007)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_workflow import (
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_SERVICE_VERSION,
    WORKFLOW_STAGES,
    apply_workflow_action,
    list_workflow_templates,
)

__all__ = [
    "apply_canonical_workflow_action",
    "institutional_workflow_schema",
    "list_canonical_workflow_templates",
]


def institutional_workflow_schema() -> dict[str, Any]:
    return {
        "schema_version": WORKFLOW_SCHEMA_VERSION,
        "service_version": WORKFLOW_SERVICE_VERSION,
        "read_only": True,
        "stages": list(WORKFLOW_STAGES),
        "actions": [
            "create",
            "transition",
            "comment",
            "get",
            "assign_reviewer",
            "history",
            "approve",
            "reject",
        ],
        "sources": [
            "research_object",
            "institutional_report",
            "research_archive",
            "research_diff",
            "decision_workspace",
            "institutional_committee",
            "investment_policy",
        ],
        "rules": [
            "workflow_state_only",
            "no_research_mutation",
            "existing_artifacts_only",
            "no_provider_calls",
            "no_engine_execution",
            "no_calculations",
            "no_valuation",
            "no_scoring",
            "no_optimisation",
            "no_recommendations",
            "missing_is_data_unavailable",
            "deterministic_transitions",
        ],
    }


def list_canonical_workflow_templates() -> list[dict[str, Any]]:
    return list_workflow_templates()


def apply_canonical_workflow_action(
    *,
    action: str,
    subject: str | None = None,
    workflow_id: str | None = None,
    template_id: str | None = None,
    artifact_refs: Mapping[str, Any] | None = None,
    reviewers: list[Mapping[str, Any]] | None = None,
    to_stage: str | None = None,
    actor_id: str | None = None,
    author_id: str | None = None,
    body: str | None = None,
    reason: str | None = None,
    note: str | None = None,
    comment_id: str | None = None,
    approval_id: str | None = None,
    event_id: str | None = None,
    reviewer_id: str | None = None,
    role: str | None = None,
    display_name: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    result_id: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "result_id": result_id,
        "created_at": created_at,
    }
    act = str(action or "").strip().lower()
    if act == "create":
        kwargs.update(
            {
                "subject": subject,
                "template_id": template_id,
                "artifact_refs": artifact_refs,
                "reviewers": reviewers,
                "workflow_id": workflow_id,
                "actor_id": actor_id,
                "metadata": metadata,
            }
        )
    elif act in {"transition", "approve", "reject"}:
        kwargs.update(
            {
                "workflow_id": workflow_id,
                "to_stage": to_stage,
                "actor_id": actor_id or author_id,
                "reason": reason,
                "note": note,
                "approval_id": approval_id,
                "event_id": event_id,
            }
        )
    elif act == "comment":
        kwargs.update(
            {
                "workflow_id": workflow_id,
                "author_id": author_id or actor_id,
                "body": body,
                "comment_id": comment_id,
            }
        )
    elif act == "assign_reviewer":
        kwargs.update(
            {
                "workflow_id": workflow_id,
                "reviewer_id": reviewer_id or actor_id,
                "role": role or "reviewer",
                "display_name": display_name,
                "actor_id": actor_id or author_id,
            }
        )
    elif act in {"get", "history"}:
        kwargs.update({"workflow_id": workflow_id})
    return apply_workflow_action(action=action, **kwargs)
