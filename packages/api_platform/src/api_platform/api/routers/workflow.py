"""Workflow routes — HTTP → DSPPlatform.run_workflow."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import ApiResponse, WorkflowRunRequest

router = APIRouter(tags=["workflow"])


@router.post("/workflow/run", response_model=ApiResponse)
def run_workflow(
    body: WorkflowRunRequest,
    state: ApiState = Depends(get_api_state),
) -> ApiResponse:
    """Delegate workflow execution to ``DSPPlatform.run_workflow``.

    Requires an opaque engine context registered under ``context_ref``
    (ephemeral API ContextStore) — the API never builds workflow graphs.
    """
    if not body.context_ref:
        raise ApiValidationError(
            "workflow/run requires context_ref to an EngineContext handle"
        )

    context = state.contexts.get(body.context_ref)
    result = state.platform.run_workflow(context)
    limitations = list(result.limitations)
    if body.note:
        limitations.append(body.note)
    return ApiResponse(
        ok=result.ok,
        capability=result.capability,
        payload={
            "context_ref": body.context_ref,
            "status": getattr(getattr(result.payload, "status", None), "value", None),
            "result_type": type(result.payload).__name__
            if result.payload is not None
            else None,
        },
        limitations=limitations,
        errors=list(result.errors),
        api_version=state.api_version,
        platform_version=result.metadata.version,
    )
