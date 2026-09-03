"""Copilot routes — EPIC-012 complete/stream + RC1 M7 Copilot 2.0 orchestration."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from api_platform.api.copilot_schemas import (
    CopilotCompleteRequest,
    CopilotCompleteResponse,
    CopilotProviderInfo,
)
from api_platform.api.copilot_v2_schemas import CopilotV2Request
from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_live_ai_activation,
)
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import ApiResponse, CopilotChatRequest

router = APIRouter(tags=["copilot"])


def _run_v2(state: ApiState, body: CopilotV2Request, *, default_mode: str | None) -> JSONResponse:
    message = body.resolved_message()
    if not message:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "message required",
                "message": "Data unavailable.",
            },
        )
    try:
        result = state.platform.run_copilot_v2(
            message=message,
            mode=body.mode or default_mode,
            conversation_id=body.conversation_id,
            symbol=body.symbol,
            symbols=body.symbols,
            portfolio_id=body.portfolio_id,
            analyse_response=body.analyse_response,
            secondary_analyse_response=body.secondary_analyse_response,
            research_object=body.research_object,
            report=body.report,
            portfolio=body.portfolio,
            portfolio_intelligence=body.portfolio_intelligence,
            committee_result=body.committee_result,
            comparison_result=body.comparison_result,
            document_kind=body.document_kind,
            workspace=body.workspace,
            buffett_mode=body.buffett_mode,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    return JSONResponse({"ok": True, "result": result, "message": result.get("message")})


@router.get("/copilot/schema")
def copilot_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Copilot 2.0 schema descriptor (RC1 Milestone 7)."""
    return {"ok": True, "schema": state.platform.copilot_v2_schema()}


@router.post("/copilot/chat", response_model=None)
def copilot_chat(
    body: CopilotV2Request,
    state: ApiState = Depends(get_api_state),
) -> ApiResponse | JSONResponse:
    """Copilot chat — M7 orchestration when ``message``/``user_text`` present.

    Legacy J1 path: supply ``context_ref`` without ``message`` to use
    ``DSPPlatform.ask_copilot`` + ContextStore.
    """
    if body.context_ref and not body.resolved_message():
        legacy = CopilotChatRequest(
            context_ref=body.context_ref,
            user_text=body.user_text,
            note=body.note,
        )
        context = state.contexts.get(legacy.context_ref)
        result = state.platform.ask_copilot(
            context,
            language_model=state.language_model,
        )
        limitations = list(result.limitations)
        if legacy.user_text:
            limitations.append("user_text accepted as transport metadata only")
        if legacy.note:
            limitations.append(legacy.note)
        payload = result.payload
        response_preview = None
        if payload is not None and hasattr(payload, "response"):
            response_preview = {
                "status": getattr(getattr(payload, "status", None), "value", None),
                "executive_summary": getattr(payload, "executive_summary", None),
            }
        return ApiResponse(
            ok=result.ok,
            capability=result.capability,
            payload={
                "context_ref": legacy.context_ref,
                "reporting": response_preview,
            },
            limitations=limitations,
            errors=list(result.errors),
            api_version=state.api_version,
            platform_version=result.metadata.version,
        )

    return _run_v2(state, body, default_mode="chat")


@router.post("/copilot/company")
def copilot_company(
    body: CopilotV2Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _run_v2(state, body, default_mode="company")


@router.post("/copilot/portfolio")
def copilot_portfolio(
    body: CopilotV2Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _run_v2(state, body, default_mode="portfolio")


@router.post("/copilot/valuation")
def copilot_valuation(
    body: CopilotV2Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _run_v2(state, body, default_mode="valuation")


@router.post("/copilot/comparison")
def copilot_comparison(
    body: CopilotV2Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _run_v2(state, body, default_mode="comparison")


@router.post("/copilot/document")
def copilot_document(
    body: CopilotV2Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _run_v2(state, body, default_mode="document")


@router.get("/copilot/history")
def copilot_history_list(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "conversations": state.platform.list_copilot_history()}


@router.get("/copilot/history/{conversation_id}")
def copilot_history_get(
    conversation_id: str,
    state: ApiState = Depends(get_api_state),
) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.get_copilot_history(conversation_id)}


@router.delete("/copilot/history/{conversation_id}")
def copilot_history_delete(
    conversation_id: str,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    deleted = state.platform.delete_copilot_history(conversation_id)
    if not deleted:
        return JSONResponse(
            status_code=404,
            content={
                "ok": False,
                "error": "not found",
                "message": "Data unavailable.",
            },
        )
    return JSONResponse({"ok": True, "deleted": True, "message": None})


@router.post("/copilot/complete", response_model=CopilotCompleteResponse)
def copilot_complete(
    body: CopilotCompleteRequest,
    state: ApiState = Depends(get_api_state),  # noqa: B008
    _activation: Any = Depends(require_live_ai_activation),  # noqa: B008
) -> CopilotCompleteResponse:
    """Complete a copilot answer via backend LLM after production activation."""
    del _activation
    if state.copilot_service is None:
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
    state: ApiState = Depends(get_api_state),  # noqa: B008
    _activation: Any = Depends(require_live_ai_activation),  # noqa: B008
) -> StreamingResponse:
    """Stream copilot answer deltas via Server-Sent Events after activation."""
    del _activation
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
