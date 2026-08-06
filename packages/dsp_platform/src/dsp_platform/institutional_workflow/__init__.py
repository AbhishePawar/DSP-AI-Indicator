"""Institutional Workflow & Approval System (EPIC-A007)."""

from __future__ import annotations

from dsp_platform.institutional_workflow.models import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STAGES,
    UNAVAILABLE_MESSAGE,
    WORKFLOW_SCHEMA_VERSION,
    WORKFLOW_SERVICE_VERSION,
    WORKFLOW_STAGES,
    ApprovalRecord,
    CommentRecord,
    DecisionEvent,
    ReviewerRecord,
    WorkflowInstance,
    WorkflowResult,
    freeze_mapping,
    utc_now,
)
from dsp_platform.institutional_workflow.registry import (
    WorkflowRegistry,
    get_workflow_registry,
    reset_workflow_registry_for_tests,
)
from dsp_platform.institutional_workflow.serde import (
    workflow_result_from_dict,
    workflow_result_to_dict,
)
from dsp_platform.institutional_workflow.service import (
    WorkflowService,
    apply_workflow_action,
)
from dsp_platform.institutional_workflow.templates import (
    DEFAULT_TEMPLATE_ID,
    get_workflow_template,
    list_workflow_templates,
)
from dsp_platform.institutional_workflow.validation import (
    InstitutionalWorkflowValidationError,
    validate_workflow_result,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "DEFAULT_TEMPLATE_ID",
    "TERMINAL_STAGES",
    "UNAVAILABLE_MESSAGE",
    "WORKFLOW_SCHEMA_VERSION",
    "WORKFLOW_SERVICE_VERSION",
    "WORKFLOW_STAGES",
    "ApprovalRecord",
    "CommentRecord",
    "DecisionEvent",
    "InstitutionalWorkflowValidationError",
    "ReviewerRecord",
    "WorkflowInstance",
    "WorkflowRegistry",
    "WorkflowResult",
    "WorkflowService",
    "apply_workflow_action",
    "freeze_mapping",
    "get_workflow_registry",
    "get_workflow_template",
    "list_workflow_templates",
    "reset_workflow_registry_for_tests",
    "utc_now",
    "validate_workflow_result",
    "workflow_result_from_dict",
    "workflow_result_to_dict",
]
