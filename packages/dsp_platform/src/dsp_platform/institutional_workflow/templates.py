"""Workflow templates (EPIC-A007)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_workflow.models import (
    ALLOWED_TRANSITIONS,
    WORKFLOW_STAGES,
    freeze_mapping,
)

__all__ = [
    "DEFAULT_TEMPLATE_ID",
    "get_workflow_template",
    "list_workflow_templates",
]

DEFAULT_TEMPLATE_ID = "institutional_research_v1"

_TEMPLATES: dict[str, Mapping[str, Any]] = {
    DEFAULT_TEMPLATE_ID: freeze_mapping(
        {
            "template_id": DEFAULT_TEMPLATE_ID,
            "name": "Institutional Research Lifecycle",
            "version": "1.0.0",
            "stages": list(WORKFLOW_STAGES),
            "transitions": {k: list(v) for k, v in ALLOWED_TRANSITIONS.items()},
            "required_artifact_keys": [
                "research_object_id",
                "report_id",
            ],
            "optional_artifact_keys": [
                "snapshot_id",
                "diff_id",
                "workspace_id",
                "committee_report_id",
                "compliance_result_id",
            ],
            "rules": [
                "workflow_state_only",
                "no_research_mutation",
                "deterministic_transitions",
            ],
        }
    )
    or freeze_mapping({}),
}


def list_workflow_templates() -> list[dict[str, Any]]:
    return [
        {
            "template_id": t["template_id"],
            "name": t["name"],
            "version": t["version"],
        }
        for t in sorted(_TEMPLATES.values(), key=lambda x: str(x["template_id"]))
    ]


def get_workflow_template(template_id: str | None = None) -> Mapping[str, Any]:
    tid = str(template_id or DEFAULT_TEMPLATE_ID)
    if tid not in _TEMPLATES:
        raise ValueError(f"unknown workflow template {tid!r}")
    return _TEMPLATES[tid]
