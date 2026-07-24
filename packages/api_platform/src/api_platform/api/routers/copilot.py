"""Copilot routes — HTTP → DSPPlatform.ask_copilot."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import ApiResponse, CopilotChatRequest

router = APIRouter(tags=["copilot"])


@router.post("/copilot/chat", response_model=ApiResponse)
def copilot_chat(
    body: CopilotChatRequest,
    state: ApiState = Depends(get_api_state),
) -> ApiResponse:
    """Delegate chat to ``DSPPlatform.ask_copilot``.

    Requires a conversation context handle in the ephemeral ContextStore.
    The API does not invent intents, explanations, or financial conclusions.
    """
    if not body.context_ref:
        raise ApiValidationError(
            "copilot/chat requires context_ref to a ConversationEngineContext"
        )

    context = state.contexts.get(body.context_ref)
    # Optional user_text overlay is presentation-only metadata for adapters;
    # domain context remains authoritative.
    result = state.platform.ask_copilot(context)
    limitations = list(result.limitations)
    if body.user_text:
        limitations.append("user_text accepted as transport metadata only")
    if body.note:
        limitations.append(body.note)
    payload = result.payload
    response_preview = None
    if payload is not None and hasattr(payload, "response"):
        response_preview = {
            "status": getattr(
                getattr(payload, "status", None), "value", None
            ),
            "executive_summary": getattr(payload, "executive_summary", None),
        }
    return ApiResponse(
        ok=result.ok,
        capability=result.capability,
        payload={
            "context_ref": body.context_ref,
            "reporting": response_preview,
        },
        limitations=limitations,
        errors=list(result.errors),
        api_version=state.api_version,
        platform_version=result.metadata.version,
    )
