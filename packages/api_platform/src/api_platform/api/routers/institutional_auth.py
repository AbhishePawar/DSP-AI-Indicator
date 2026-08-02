"""Additive Institutional Auth & RBAC routes (EPIC-A009).

Does not replace legacy ``/auth/login`` (security_platform). Paths live under
``/auth/rbac/*`` for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["auth-rbac"])


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=12, max_length=256)
    display_name: str | None = Field(None, max_length=128)
    roles: list[str] | None = None
    user_id: str | None = Field(None, max_length=128)
    created_at: str | None = Field(None, max_length=64)
    password_salt: str | None = Field(None, max_length=64)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)
    created_at: str | None = Field(None, max_length=64)
    session_id: str | None = Field(None, max_length=128)
    access_jti: str | None = Field(None, max_length=128)
    refresh_jti: str | None = Field(None, max_length=128)


class LogoutRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    updated_at: str | None = Field(None, max_length=64)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16)
    created_at: str | None = Field(None, max_length=64)
    access_jti: str | None = Field(None, max_length=128)


class SetRolesRequest(BaseModel):
    roles: list[str] = Field(..., min_length=1)


class UpsertRoleRequest(BaseModel):
    role_id: str = Field(..., min_length=1, max_length=64)
    name: str | None = Field(None, max_length=128)
    permissions: list[str] | None = None


class EvaluatePermissionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    permission: str = Field(..., min_length=1, max_length=64)


def _err(exc: Exception, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": str(exc), "message": "Data unavailable."},
    )


@router.get("/auth/rbac/schema")
def rbac_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.auth_schema()}


@router.post("/auth/rbac/login")
def rbac_login(
    body: LoginRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.auth_login(
            username=body.username,
            password=body.password,
            created_at=body.created_at,
            session_id=body.session_id,
            access_jti=body.access_jti,
            refresh_jti=body.refresh_jti,
        )
    except Exception as exc:  # noqa: BLE001
        status = 401 if "credential" in str(exc).lower() else 400
        return _err(exc, status=status)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/auth/rbac/logout")
def rbac_logout(
    body: LogoutRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.auth_logout(
            session_id=body.session_id, updated_at=body.updated_at
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/auth/rbac/refresh")
def rbac_refresh(
    body: RefreshRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.auth_refresh(
            refresh_token=body.refresh_token,
            created_at=body.created_at,
            access_jti=body.access_jti,
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=401)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/auth/rbac/me")
def rbac_me(
    state: ApiState = Depends(get_api_state),
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        return _err(ValueError("Bearer token required"), status=401)
    token = authorization.split(" ", 1)[1].strip()
    try:
        result = state.platform.auth_current_user(token)
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=401)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/auth/rbac/users")
def create_user(
    body: CreateUserRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.create_auth_user(
            username=body.username,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            roles=body.roles,
            user_id=body.user_id,
            created_at=body.created_at,
            password_salt=body.password_salt,
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/auth/rbac/users")
def list_users(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.list_auth_users()}


@router.get("/auth/rbac/users/{user_id}")
def get_user(
    user_id: str, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    result = state.platform.get_auth_user(user_id)
    if result is None:
        return _err(ValueError("not found"), status=404)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.put("/auth/rbac/users/{user_id}/roles")
def set_roles(
    user_id: str,
    body: SetRolesRequest,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    try:
        result = state.platform.set_auth_user_roles(user_id, body.roles)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/auth/rbac/roles")
def list_roles(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.list_auth_roles()}


@router.post("/auth/rbac/roles")
def upsert_role(
    body: UpsertRoleRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.upsert_auth_role(
            body.role_id, name=body.name, permissions=body.permissions
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/auth/rbac/permissions")
def list_permissions(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "result": state.platform.list_auth_permissions()}


@router.post("/auth/rbac/evaluate")
def evaluate_permission(
    body: EvaluatePermissionRequest, state: ApiState = Depends(get_api_state)
) -> JSONResponse:
    try:
        result = state.platform.evaluate_auth_permission(
            body.user_id, body.permission
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/auth/rbac/protect")
def protect_endpoint(
    state: ApiState = Depends(get_api_state),
    authorization: str | None = Header(default=None),
    permission: str = "read_research",
) -> JSONResponse:
    """Optional guard: validate bearer token + permission. Default APIs stay open."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return _err(ValueError("Bearer token required"), status=401)
    token = authorization.split(" ", 1)[1].strip()
    try:
        result = state.platform.protect_with_permission(token, permission)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        status = 403 if "permission" in msg or "missing" in msg else 401
        return _err(exc, status=status)
    return JSONResponse({"ok": True, "result": result, "message": None})
