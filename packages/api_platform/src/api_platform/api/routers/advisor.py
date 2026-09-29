"""Advisor routes — Figma Advisor page (client book).

Every route is per-advisor: the client book belongs to the authenticated user
(P0-05: identity from server-validated JWT only). Portfolio value is an
advisor-entered figure; when absent the client receives ``null`` and the UI
must render "Data unavailable." (CV-001). No rating is computed here — a
client rating requires the DSP research pipeline and is therefore omitted.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_authenticated_actor,
)

router = APIRouter(tags=["advisor"])


def _validation_error(exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"ok": False, "error": str(exc), "message": "Unable to save."},
    )


def _is_validation_error(exc: Exception) -> bool:
    return type(exc).__name__ == "WorkspaceValidationError" or isinstance(exc, ValueError)


class ClientUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=120)
    risk_profile: str = Field(..., min_length=1, max_length=32)
    email: str | None = Field(None, max_length=254)
    portfolio_value: float | None = Field(None, ge=0)
    notes: str | None = Field(None, max_length=1000)


def _overview(clients: list[dict[str, Any]]) -> dict[str, Any]:
    values = [c["portfolio_value"] for c in clients if isinstance(c.get("portfolio_value"), (int, float))]
    return {
        "active_clients": len(clients),
        # Sum only over clients that carry an advisor-entered value; report how
        # many were excluded so the UI can state coverage honestly.
        "total_portfolio_value": float(sum(values)) if values else None,
        "clients_with_portfolio_value": len(values),
        "research_sessions": int(sum(int(c.get("research_sessions") or 0) for c in clients)),
        "risk_profile_counts": {
            level: sum(1 for c in clients if c.get("risk_profile") == level)
            for level in ("conservative", "moderate", "aggressive")
        },
    }


@router.get("/advisor/clients")
def list_clients(
    request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    clients = state.platform.investor_workspace().store.list_clients(actor["user_id"])
    return {"ok": True, "items": clients, "count": len(clients), "overview": _overview(clients)}


@router.post("/advisor/clients", status_code=201)
def create_client(
    body: ClientUpsertRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    store = state.platform.investor_workspace().store
    try:
        record = store.upsert_client(actor["user_id"], **body.model_dump())
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    return JSONResponse(status_code=201, content={"ok": True, "item": record})


@router.get("/advisor/clients/{client_id}")
def get_client(
    client_id: str, request: Request, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    item = state.platform.investor_workspace().store.get_client(actor["user_id"], client_id)
    if item is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "client not found"})
    return JSONResponse({"ok": True, "item": item})


@router.put("/advisor/clients/{client_id}")
def update_client(
    client_id: str,
    body: ClientUpsertRequest,
    request: Request,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    actor = require_authenticated_actor(request)
    store = state.platform.investor_workspace().store
    if store.get_client(actor["user_id"], client_id) is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "client not found"})
    try:
        record = store.upsert_client(actor["user_id"], client_id=client_id, **body.model_dump())
    except Exception as exc:  # noqa: BLE001
        if _is_validation_error(exc):
            return _validation_error(exc)
        raise
    return JSONResponse({"ok": True, "item": record})


@router.post("/advisor/clients/{client_id}/sessions")
def record_client_session(
    client_id: str, request: Request, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    """Count a research session opened for this client (Figma "View →")."""
    actor = require_authenticated_actor(request)
    item = state.platform.investor_workspace().store.record_client_session(
        actor["user_id"], client_id
    )
    if item is None:
        return JSONResponse(status_code=404, content={"ok": False, "error": "client not found"})
    return JSONResponse({"ok": True, "item": item})


@router.delete("/advisor/clients/{client_id}")
def delete_client(
    client_id: str, request: Request, state: ApiState = Depends(get_api_state)
) -> dict[str, Any]:
    actor = require_authenticated_actor(request)
    store = state.platform.investor_workspace().store
    return {"ok": True, "removed": store.delete_client(actor["user_id"], client_id)}
