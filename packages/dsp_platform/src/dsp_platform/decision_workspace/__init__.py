"""Institutional Decision Workspace (EPIC-A004)."""

from __future__ import annotations

from dsp_platform.decision_workspace.models import (
    PANEL_NAMES,
    UNAVAILABLE_MESSAGE,
    WORKSPACE_KINDS,
    WORKSPACE_SCHEMA_VERSION,
    WORKSPACE_SERVICE_VERSION,
    TimelineEvent,
    WorkspacePanel,
    WorkspaceResult,
    freeze_mapping,
    utc_now,
)
from dsp_platform.decision_workspace.serde import (
    workspace_result_from_dict,
    workspace_result_to_dict,
)
from dsp_platform.decision_workspace.service import (
    DecisionWorkspaceService,
    build_decision_workspace,
)
from dsp_platform.decision_workspace.validation import (
    DecisionWorkspaceValidationError,
    validate_workspace_result,
)

__all__ = [
    "PANEL_NAMES",
    "UNAVAILABLE_MESSAGE",
    "WORKSPACE_KINDS",
    "WORKSPACE_SCHEMA_VERSION",
    "WORKSPACE_SERVICE_VERSION",
    "DecisionWorkspaceService",
    "DecisionWorkspaceValidationError",
    "TimelineEvent",
    "WorkspacePanel",
    "WorkspaceResult",
    "build_decision_workspace",
    "freeze_mapping",
    "utc_now",
    "validate_workspace_result",
    "workspace_result_from_dict",
    "workspace_result_to_dict",
]
