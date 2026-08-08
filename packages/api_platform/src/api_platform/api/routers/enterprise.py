"""Additive Enterprise Commercial Platform routes (EPS-002).

Mounted under ``/enterprise/*`` and ``/api/v1/enterprise/*``.
Does not modify research / valuation / recommendation contracts.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_admin_access,
    require_authenticated_actor,
)
from enterprise import (
    ForbiddenError,
    NotFoundError,
    ValidationError,
    get_enterprise_service,
)

router = APIRouter(tags=["enterprise"])


def _err(exc: Exception, status: int = 400) -> JSONResponse:
    if isinstance(exc, ForbiddenError):
        status = 403
    elif isinstance(exc, NotFoundError):
        status = 404
    elif isinstance(exc, ValidationError):
        status = 400
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": str(exc), "message": "Data unavailable."},
    )


def _actor(auth: dict[str, Any]) -> str:
    """P0-05 — actor is always the authenticated server principal."""
    actor = str(auth.get("user_id") or "").strip()
    if not actor:
        raise HTTPException(status_code=401, detail="authentication required")
    return actor


# ---- request bodies --------------------------------------------------------


class CreateOrgBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    slug: str = Field(..., min_length=3, max_length=64)
    owner_user_id: str | None = Field(None, max_length=128)
    org_id: str | None = Field(None, max_length=128)
    seat_limit: int | None = Field(None, ge=1, le=100000)
    branding: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class UpdateOrgBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    name: str | None = Field(None, max_length=128)
    status: str | None = Field(None, max_length=32)
    branding: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    seat_limit: int | None = Field(None, ge=1, le=100000)


class CreateTeamBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    kind: str = Field(default="custom", max_length=32)
    parent_team_id: str | None = Field(None, max_length=128)
    team_id: str | None = Field(None, max_length=128)


class AddMemberBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    user_id: str = Field(..., min_length=1, max_length=128)
    role_id: str = Field(..., min_length=1, max_length=64)
    display_name: str | None = Field(None, max_length=128)
    email: str | None = Field(None, max_length=256)


class SetRoleBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    role_id: str = Field(..., min_length=1, max_length=64)


class InviteBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    email: str = Field(..., min_length=3, max_length=256)
    role_id: str = Field(..., min_length=1, max_length=64)


class AssignLicenseBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    tier: str = Field(..., min_length=1, max_length=32)
    seats: int = Field(..., ge=1, le=100000)
    expires_at: str | None = Field(None, max_length=64)
    usage_limits: dict[str, Any] | None = None


class CreateApiKeyBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    name: str = Field(..., min_length=1, max_length=128)
    scopes: list[str] = Field(..., min_length=1)
    expires_at: str | None = Field(None, max_length=64)


class CreateSessionBody(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    device_label: str = Field(default="unknown", max_length=128)
    ip_hint: str | None = Field(None, max_length=64)
    user_agent_hint: str | None = Field(None, max_length=256)


class EvaluateBody(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    permission: str = Field(..., min_length=1, max_length=64)


class AuditEventBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    action: str = Field(..., min_length=1, max_length=64)
    resource_type: str = Field(..., min_length=1, max_length=64)
    resource_id: str | None = Field(None, max_length=128)
    metadata: dict[str, Any] | None = None


class CustomRoleBody(BaseModel):
    actor_user_id: str | None = Field(None, max_length=128)
    role_id: str = Field(..., min_length=1, max_length=64)
    name: str | None = Field(None, max_length=128)
    permissions: list[str] | None = None


# ---- routes ----------------------------------------------------------------


@router.get("/enterprise/schema")
def enterprise_schema() -> dict[str, Any]:
    return {"ok": True, "schema": get_enterprise_service().schema()}


@router.get("/enterprise/organizations")
def list_organizations(
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> dict[str, Any]:
    svc = get_enterprise_service()
    rows = svc.list_organizations(user_id=_actor(auth))
    return {
        "ok": True,
        "result": rows,
        "message": None if rows else "No organizations available.",
    }


@router.post("/enterprise/organizations")
def create_organization(
    body: CreateOrgBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        data = body.model_dump()
        # P0-05 — owner identity is the authenticated principal only.
        data["owner_user_id"] = _actor(auth)
        result = get_enterprise_service().create_organization(**data)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}")
def get_organization(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    result = get_enterprise_service().get_organization(org_id)
    if result is None:
        return _err(NotFoundError("organization not found"), status=404)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.patch("/enterprise/organizations/{org_id}")
def update_organization(
    org_id: str,
    body: UpdateOrgBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        data = body.model_dump()
        data.pop("actor_user_id", None)
        actor = _actor(auth)
        result = get_enterprise_service().update_organization(
            org_id, actor_user_id=actor, **data
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}/teams")
def list_teams(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().list_teams(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse(
        {
            "ok": True,
            "result": result,
            "message": None if result else "No teams available.",
        }
    )


@router.post("/enterprise/organizations/{org_id}/teams")
def create_team(
    org_id: str,
    body: CreateTeamBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        data = body.model_dump()
        data.pop("actor_user_id", None)
        actor = _actor(auth)
        result = get_enterprise_service().create_team(
            org_id, actor_user_id=actor, **data
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}/members")
def list_members(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().list_members(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse(
        {
            "ok": True,
            "result": result,
            "message": None if result else "No members available.",
        }
    )


@router.post("/enterprise/organizations/{org_id}/members")
def add_member(
    org_id: str,
    body: AddMemberBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        data = body.model_dump()
        data.pop("actor_user_id", None)
        actor = _actor(auth)
        result = get_enterprise_service().add_member(
            org_id, actor_user_id=actor, **data
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.put("/enterprise/organizations/{org_id}/members/{user_id}/role")
def set_member_role(
    org_id: str,
    user_id: str,
    body: SetRoleBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        result = get_enterprise_service().set_member_role(
            org_id, user_id, body.role_id, actor_user_id=_actor(auth)
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/enterprise/organizations/{org_id}/invitations")
def invite_member(
    org_id: str,
    body: InviteBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        result = get_enterprise_service().invite_member(
            org_id,
            email=body.email,
            role_id=body.role_id,
            actor_user_id=_actor(auth),
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}/roles")
def list_roles(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> dict[str, Any]:
    return {"ok": True, "result": get_enterprise_service().list_roles(org_id)}


@router.post("/enterprise/organizations/{org_id}/roles")
def upsert_role(
    org_id: str,
    body: CustomRoleBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        result = get_enterprise_service().upsert_custom_role(
            org_id,
            body.role_id,
            name=body.name,
            permissions=body.permissions,
            actor_user_id=_actor(auth),
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/enterprise/organizations/{org_id}/permissions/evaluate")
def evaluate_permission(
    org_id: str,
    body: EvaluateBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": get_enterprise_service().evaluate_permission(
            org_id, body.user_id, body.permission
        ),
    }


@router.get("/enterprise/organizations/{org_id}/license")
def get_license(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().get_license(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": result.get("message")})


@router.post("/enterprise/organizations/{org_id}/license")
def assign_license(
    org_id: str,
    body: AssignLicenseBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        data = body.model_dump()
        data.pop("actor_user_id", None)
        actor = _actor(auth)
        result = get_enterprise_service().assign_license(
            org_id, actor_user_id=actor, **data
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}/billing")
def billing_status(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().billing_status(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse(
        {
            "ok": True,
            "result": result,
            "message": result.get("message") or "Billing unavailable.",
        }
    )


@router.get("/enterprise/organizations/{org_id}/invoices")
def list_invoices(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().list_invoices(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse(
        {"ok": True, "result": result, "message": result.get("message")}
    )


@router.get("/enterprise/organizations/{org_id}/portal")
def customer_portal(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().customer_portal(
            org_id, actor_user_id=actor
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}/sessions")
def list_sessions(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().list_sessions(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse(
        {
            "ok": True,
            "result": result,
            "message": None if result else "No active sessions.",
        }
    )


@router.post("/enterprise/organizations/{org_id}/sessions")
def create_session(
    org_id: str,
    body: CreateSessionBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        data = body.model_dump()
        # P0-05 — session principal is the authenticated actor only.
        data["user_id"] = _actor(auth)
        result = get_enterprise_service().create_session(org_id, **data)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/enterprise/organizations/{org_id}/sessions/{session_id}/revoke")
def revoke_session(
    org_id: str,
    session_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().revoke_session(
            org_id, session_id, actor_user_id=actor
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}/audit")
def list_audit(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().list_audit(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse(
        {
            "ok": True,
            "result": result,
            "message": None if result else "No audit records.",
        }
    )


@router.post("/enterprise/organizations/{org_id}/audit")
def record_audit(
    org_id: str,
    body: AuditEventBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        result = get_enterprise_service().record_audit(
            org_id=org_id,
            actor_user_id=_actor(auth),
            action=body.action,
            resource_type=body.resource_type,
            resource_id=body.resource_id,
            metadata=body.metadata,
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.delete("/enterprise/organizations/{org_id}/audit/{event_id}")
def delete_audit_forbidden(
    org_id: str,
    event_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        get_enterprise_service().mutate_audit_forbidden(event_id)
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=403)
    return JSONResponse(status_code=403, content={"ok": False, "error": "forbidden"})


@router.get("/enterprise/organizations/{org_id}/api-keys")
def list_api_keys(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().list_api_keys(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse(
        {"ok": True, "result": result, "message": result.get("message")}
    )


@router.post("/enterprise/organizations/{org_id}/api-keys")
def create_api_key(
    org_id: str,
    body: CreateApiKeyBody,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        result = get_enterprise_service().create_api_key(
            org_id,
            name=body.name,
            scopes=body.scopes,
            actor_user_id=_actor(auth),
            expires_at=body.expires_at,
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/enterprise/organizations/{org_id}/api-keys/{key_id}/rotate")
def rotate_api_key(
    org_id: str,
    key_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().rotate_api_key(
            org_id, key_id, actor_user_id=actor
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.post("/enterprise/organizations/{org_id}/api-keys/{key_id}/disable")
def disable_api_key(
    org_id: str,
    key_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().disable_api_key(
            org_id, key_id, actor_user_id=actor
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": None})


@router.get("/enterprise/organizations/{org_id}/usage")
def usage_snapshot(
    org_id: str,
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    try:
        actor = _actor(auth)
        result = get_enterprise_service().usage_snapshot(org_id, actor_user_id=actor)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)
    return JSONResponse({"ok": True, "result": result, "message": result.get("message")})


@router.get("/enterprise/ops/incident-center")
def incident_center(
    state: ApiState = Depends(get_api_state),
    _admin: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": get_enterprise_service().incident_center(
            infrastructure=state.infrastructure
        ),
    }


@router.get("/enterprise/ops/dashboard")
def ops_dashboard(
    state: ApiState = Depends(get_api_state),
    _admin: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    return {
        "ok": True,
        "result": get_enterprise_service().operational_dashboard(
            infrastructure=state.infrastructure
        ),
    }


@router.get("/enterprise/ops/usage")
def platform_usage(
    _admin: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    return {"ok": True, "result": get_enterprise_service().platform_usage_analytics()}


@router.get("/enterprise/admin/overview")
def admin_overview(
    _admin: dict[str, Any] = Depends(require_admin_access),
) -> dict[str, Any]:
    return {"ok": True, "result": get_enterprise_service().admin_overview()}


@router.get("/enterprise/collaboration/architecture")
def collaboration_architecture() -> dict[str, Any]:
    return {
        "ok": True,
        "result": get_enterprise_service().collaboration.architecture(),
    }
