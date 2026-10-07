"""Copilot routes — EPIC-012 complete/stream + RC1 M7 Copilot 2.0 orchestration."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, StreamingResponse
from api_platform.api.dependencies import require_authenticated_actor

from api_platform.api.copilot_schemas import (
    CopilotCompleteRequest,
    CopilotCompleteResponse,
    CopilotProviderInfo,
)
from api_platform.api.copilot_v2_schemas import CopilotV2Request
from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.exceptions import ApiValidationError
from api_platform.api.schemas import ApiResponse, CopilotChatRequest

router = APIRouter(tags=["copilot"])


def _run_v2(
    state: ApiState,
    body: CopilotV2Request,
    *,
    default_mode: str | None,
    user_id: str | None = None,
    analysis_id: str | None = None,
    idempotency_key: str | None = None,
    require_ai: bool = False,
) -> JSONResponse:
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
            analysis_id=analysis_id or body.analysis_id,
            user_id=user_id,
            idempotency_key=idempotency_key or body.idempotency_key,
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
            research_orchestrator=state.research_orchestrator,
            language_model=state.language_model,
            provider_registry=getattr(state.copilot_service, "_registry", None) if state.copilot_service else None,
            require_ai=require_ai,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "Generation failed.", "message": "Data unavailable."},
        )
    return JSONResponse(
        {"ok": True, "result": result, "message": result.get("message")}
    )


@router.get("/copilot/schema")
def copilot_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    """Copilot 2.0 schema descriptor (RC1 Milestone 7)."""
    return {"ok": True, "schema": state.platform.copilot_v2_schema()}


@router.post("/copilot/chat", response_model=None)
def copilot_chat(
    body: CopilotV2Request,
    state: ApiState = Depends(get_api_state),
    actor: dict[str, Any] = Depends(require_authenticated_actor),
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    x_idempotency_key_header: str | None = Header(None, alias="X-Idempotency-Key"),
) -> ApiResponse | JSONResponse:
    user_id = str(actor.get("user_id") or "").strip()
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

    clean_symbol = (body.symbol or "").strip()
    clean_analysis_id = (body.analysis_id or "").strip()
    if not clean_symbol or not clean_analysis_id:
        return JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "error": "symbol and analysis_id required for durable copilot session",
                "message": "Data unavailable.",
            },
        )

    effective_idempotency_key = (
        idempotency_key_header
        or x_idempotency_key_header
        or body.idempotency_key
        or None
    )
    if effective_idempotency_key:
        effective_idempotency_key = effective_idempotency_key.strip() or None

    return _run_v2(
        state,
        body,
        default_mode=None,
        user_id=user_id,
        analysis_id=clean_analysis_id,
        idempotency_key=effective_idempotency_key,
        require_ai=True,
    )


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


@router.post("/copilot/complete", response_model=None)
def copilot_complete(
    body: CopilotCompleteRequest,
    state: ApiState = Depends(get_api_state),
) -> CopilotCompleteResponse | JSONResponse:
    """Complete a copilot answer via backend LLM with deterministic fallback."""
    if body.mode == "simple":
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "error": "COPILOT_NOT_AVAILABLE_IN_SIMPLE_MODE",
                "message": "AI Copilot is available only in Buffett AI Indicator mode.",
            },
        )
    if state.copilot_service is None:
        raise ApiValidationError("Copilot service is not configured")
    req = body.request
    if (not req or not req.get("ticker")) and body.response and isinstance(body.response, dict):
        payload = body.response.get("payload") or {}
        req = {
            "ticker": (req.get("ticker") if req else None) or payload.get("ticker") or (body.market_context or {}).get("symbol") or "",
            "company": (req.get("company") if req else None) or payload.get("company") or (body.market_context or {}).get("symbol") or "",
            "exchange": (req.get("exchange") if req else None) or payload.get("exchange"),
        }
    result = state.copilot_service.complete(
        question_id=body.question_id,
        freeform=body.freeform,
        request=req,
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


@router.post("/copilot/stream", response_model=None)
def copilot_stream(
    body: CopilotCompleteRequest,
    state: ApiState = Depends(get_api_state),
) -> StreamingResponse | JSONResponse:
    """Stream copilot answer deltas via Server-Sent Events."""
    if body.mode == "simple":
        return JSONResponse(
            status_code=403,
            content={
                "ok": False,
                "error": "COPILOT_NOT_AVAILABLE_IN_SIMPLE_MODE",
                "message": "AI Copilot is available only in Buffett AI Indicator mode.",
            },
        )
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
