"""Copilot routes — HTTP → DSPPlatform.ask_copilot + EPIC-012 complete/stream."""

from __future__ import annotations

import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from api_platform.api.copilot_schemas import (
    CopilotCompleteRequest,
    CopilotCompleteResponse,
    CopilotProviderInfo,
)
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
    result = state.platform.ask_copilot(
        context,
        language_model=state.language_model,
    )
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


@router.post("/copilot/complete", response_model=CopilotCompleteResponse)
def copilot_complete(
    body: CopilotCompleteRequest,
    state: ApiState = Depends(get_api_state),
) -> CopilotCompleteResponse:
    """Complete a copilot answer via backend LLM with deterministic fallback."""
    if state.copilot_service is None:
        from api_platform.api.exceptions import ApiValidationError

        raise ApiValidationError("Copilot service is not configured")
    result = state.copilot_service.complete(
        question_id=body.question_id,
        freeform=body.freeform,
        request=body.request,
        response=body.response,
        secondary_request=body.secondary_request,
        secondary_response=body.secondary_response,
        last_intent=body.last_intent,
        market_context=body.market_context,
    )
    return CopilotCompleteResponse(
        content=result.content,
        citations=result.citations,
        intent=result.intent,
        unavailable=result.unavailable,
        provider_id=result.provider_id,
        limitations=list(result.limitations),
    )


@router.post("/copilot/stream")
def copilot_stream(
    body: CopilotCompleteRequest,
    state: ApiState = Depends(get_api_state),
) -> StreamingResponse:
    """Stream copilot answer deltas via Server-Sent Events."""
    if state.copilot_service is None:
        raise ApiValidationError("Copilot service is not configured")

    def event_stream() -> Iterator[str]:
        provider_id = state.copilot_service.active_provider_id()
        for delta in state.copilot_service.stream(
            question_id=body.question_id,
            freeform=body.freeform,
            request=body.request,
            response=body.response,
            last_intent=body.last_intent,
            market_context=body.market_context,
        ):
            chunk = json.dumps(
                {"delta": delta, "done": False, "provider_id": provider_id}
            )
            yield f"data: {chunk}\n\n"
        yield f"data: {json.dumps({'delta': '', 'done': True, 'provider_id': provider_id})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/copilot/providers", response_model=CopilotProviderInfo)
def copilot_providers(
    state: ApiState = Depends(get_api_state),
) -> CopilotProviderInfo:
    """Capability discovery for configured LLM providers."""
    registry = state.copilot_service._registry
    active, _ = registry.resolve_active()
    return CopilotProviderInfo(
        providers=registry.list_providers(),
        active_provider=active,
    )
