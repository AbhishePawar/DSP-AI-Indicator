"""Additive Enterprise Admin & Audit Console routes (EPIC-A010).

Read-only operational visibility. Does not modify research artifacts.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state, require_admin_access

router = APIRouter(
    tags=["admin"],
    dependencies=[Depends(require_admin_access)],
)

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=12, max_length=256)
    display_name: str | None = Field(None, max_length=128)
    roles: list[str] | None = None
    user_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)
    password_salt: str | None = Field(None, max_length=64)


class SetRolesRequest(BaseModel):
    roles: list[str] = Field(..., min_length=1)


class UpsertRoleRequest(BaseModel):
    role_id: str = Field(..., min_length=1, max_length=64)
    name: str | None = Field(None, max_length=128)
    permissions: list[str] | None = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=256)
    scope: str = Field(default="audit", max_length=32)


def _err(exc: Exception, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": str(exc), "message": "Data unavailable."},
    )


@router.get("/admin/schema")
def admin_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.admin_schema()}


@router.get("/admin/dashboard")
def admin_dashboard(
    state: ApiState = Depends(get_api_state),
    generated_at: str | None = Query(default=None, max_length=64),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": state.platform.admin_dashboard(generated_at=generated_at),
    }


@router.get("/admin/users")
def list_users(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_list_users()}


@router.get("/admin/users/{user_id}")
def get_user(
    user_id: str, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    result = state.platform.admin_get_user(user_id)
    if result is None:
        return _err(ValueError("not found"), status=404)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/admin/users")
def create_user(
    body: CreateUserRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.admin_create_user(**body.model_dump())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.put("/admin/users/{user_id}/roles")
def set_roles(
    user_id: str,
    body: SetRolesRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        result = state.platform.admin_set_user_roles(user_id, body.roles)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/admin/roles")
def list_roles(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_list_roles()}


@router.post("/admin/roles")
def upsert_role(
    body: UpsertRoleRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.admin_upsert_role(**body.model_dump())
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/admin/permissions")
def list_permissions(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_list_permissions()}


@router.get("/admin/sessions")
def list_sessions(
    state: ApiState = Depends(get_api_state),
    user_id: str | None = Query(default=None, max_length=128),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": state.platform.admin_list_sessions(user_id=user_id),
    }


@router.get("/admin/audit")
def list_audit(
    state: ApiState = Depends(get_api_state),
    query: str | None = Query(default=None, max_length=256),
    subject: str | None = Query(default=None, max_length=128),
    workflow_id: str | None = Query(default=None, max_length=128),
    event_type: str | None = Query(default=None, max_length=64),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": state.platform.admin_list_audit_records(
            query=query,
            subject=subject,
            workflow_id=workflow_id,
            event_type=event_type,
        ),
    }


@router.get("/admin/workflow-history")
def workflow_history(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_list_workflow_history()}


@router.get("/admin/research-archive")
def research_archive(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {
        "ok": True,
        "result": state.platform.admin_list_research_archive_metadata(),
    }


@router.get("/admin/timeline")
def timeline(
    state: ApiState = Depends(get_api_state),
    limit: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": state.platform.admin_activity_timeline(limit=limit),
    }


@router.post("/admin/search")
def search(
    body: SearchRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.admin_search(body.query, scope=body.scope)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/admin/audit/export")
def export_audit(
    state: ApiState = Depends(get_api_state),
    query: str | None = Query(default=None, max_length=256),
    subject: str | None = Query(default=None, max_length=128),
    workflow_id: str | None = Query(default=None, max_length=128),
    event_type: str | None = Query(default=None, max_length=64),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": state.platform.admin_export_audit(
            query=query,
            subject=subject,
            workflow_id=workflow_id,
            event_type=event_type,
        ),
    }


@router.get("/admin/health")
def health_panel(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_health_panel()}


@router.get("/admin/configuration")
def configuration(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_configuration()}


@router.get("/admin/versions")
def versions(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_versions()}


@router.get("/admin/feature-flags")
def feature_flags(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_feature_flags()}


@router.get("/admin/metrics")
def metrics(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.admin_system_metrics()}
