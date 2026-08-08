"""RC1 Milestone 9 — thin Commercial SaaS Platform routes.

Delegates to DSPPlatform.run_saas_platform → enterprise domain.
Never fabricates payments or duplicates organizations/IAM.

P0-05 — actor identity comes only from authenticated JWT/session.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.dependencies import (
    ApiState,
    get_api_state,
    require_authenticated_actor,
)

router = APIRouter(tags=["saas"])


class SaasPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    org_id: str | None = Field(None, max_length=128)
    actor_user_id: str | None = Field(None, max_length=128)
    owner_user_id: str | None = Field(None, max_length=128)
    user_id: str | None = Field(None, max_length=128)
    name: str | None = Field(None, max_length=128)
    slug: str | None = Field(None, max_length=64)
    plan_id: str | None = Field(None, max_length=32)
    tier: str | None = Field(None, max_length=32)
    status: str | None = Field(None, max_length=32)
    seats: int | None = Field(None, ge=1, le=100000)
    seat_limit: int | None = Field(None, ge=1, le=100000)
    kind: str | None = Field(None, max_length=32)
    email: str | None = Field(None, max_length=256)
    role_id: str | None = Field(None, max_length=64)
    key_id: str | None = Field(None, max_length=128)
    api_key_id: str | None = Field(None, max_length=128)
    license_key: str | None = Field(None, max_length=128)
    code: str | None = Field(None, max_length=64)
    metric: str | None = Field(None, max_length=64)
    amount: int | None = Field(None, ge=1, le=1_000_000)
    hard: bool | None = None
    scopes: list[str] | None = None
    branding: dict[str, Any] | None = None
    preferences: dict[str, Any] | None = None


def _actor(auth: dict[str, Any]) -> str:
    actor = str(auth.get("user_id") or "").strip()
    if not actor:
        raise HTTPException(status_code=401, detail="authentication required")
    return actor


def _with_actor(
    auth: dict[str, Any],
    payload: dict[str, Any] | None = None,
    *,
    as_owner: bool = False,
) -> dict[str, Any]:
    """Inject server actor; strip client-supplied identity fields."""
    data = dict(payload or {})
    actor = _actor(auth)
    data.pop("actor_user_id", None)
    data.pop("owner_user_id", None)
    data.pop("user_id", None)
    data["actor_user_id"] = actor
    if as_owner:
        data["owner_user_id"] = actor
    return data


def _dispatch(
    state: ApiState,
    action: str,
    payload: dict[str, Any] | None = None,
) -> JSONResponse:
    try:
        result = state.platform.run_saas_platform(action, payload=payload)
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
    status = 200 if result.get("ok") is not False else 400
    err = str(result.get("error_type") or "")
    if err == "NotFoundError":
        status = 404
    elif err == "ForbiddenError":
        status = 403
    return JSONResponse(status_code=status, content=result)


@router.get("/saas/schema")
def saas_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.saas_platform_schema()}


@router.get("/saas/plans")
def saas_plans(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "plans")


@router.get("/saas/dashboard")
def saas_dashboard(
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(state, "dashboard", {"actor_user_id": _actor(auth)})


@router.get("/saas/organizations")
def list_organizations(
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "list_organizations",
        {"user_id": _actor(auth)},
    )


@router.post("/saas/organization")
def create_organization(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True), as_owner=True)
    return _dispatch(state, "create_organization", payload)


@router.get("/saas/organization/{org_id}")
def get_organization(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "get_organization",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.put("/saas/organization/{org_id}")
def update_organization(
    org_id: str,
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    payload["org_id"] = org_id
    return _dispatch(state, "update_organization", payload)


@router.post("/saas/organization/{org_id}/archive")
def archive_organization(
    org_id: str,
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    payload["org_id"] = org_id
    return _dispatch(state, "archive_organization", payload)


@router.delete("/saas/organization/{org_id}")
def delete_organization(
    org_id: str,
    hard: bool = Query(False),
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "delete_organization",
        {"org_id": org_id, "actor_user_id": _actor(auth), "hard": hard},
    )


@router.get("/saas/organization/{org_id}/settings")
def get_settings(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "organization_settings",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.put("/saas/organization/{org_id}/settings")
def update_settings(
    org_id: str,
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    payload["org_id"] = org_id
    return _dispatch(state, "update_settings", payload)


@router.post("/saas/team")
def create_team(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "create_team", payload)


@router.get("/saas/organization/{org_id}/teams")
def list_teams(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "list_teams",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.post("/saas/organization/{org_id}/invite")
def invite_member(
    org_id: str,
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    payload["org_id"] = org_id
    return _dispatch(state, "invite_member", payload)


@router.post("/saas/subscription")
def create_subscription(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "create_subscription", payload)


@router.get("/saas/organization/{org_id}/subscription")
def get_subscription(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "get_subscription",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.post("/saas/license")
def assign_license(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "assign_license", payload)


@router.post("/saas/license/key")
def issue_license_key(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "issue_license_key", payload)


@router.post("/saas/license/activate")
def activate_license(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "activate_license", payload)


@router.get("/saas/organization/{org_id}/license")
def get_license(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "get_license",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.post("/saas/api-key")
def create_api_key(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "create_api_key", payload)


@router.post("/saas/api-key/rotate")
def rotate_api_key(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "rotate_api_key", payload)


@router.post("/saas/api-key/revoke")
def revoke_api_key(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "revoke_api_key", payload)


@router.get("/saas/organization/{org_id}/api-keys")
def list_api_keys(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "list_api_keys",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.post("/saas/usage")
def record_usage(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "record_usage", payload)


@router.get("/saas/organization/{org_id}/usage")
def get_usage(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "usage",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.get("/saas/organization/{org_id}/billing")
def billing_status(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "billing_status",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.put("/saas/organization/{org_id}/billing-profile")
def upsert_billing_profile(
    org_id: str,
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    payload["org_id"] = org_id
    return _dispatch(state, "upsert_billing_profile", payload)


@router.get("/saas/organization/{org_id}/billing-profile")
def get_billing_profile(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "billing_profile",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.get("/saas/organization/{org_id}/limits")
def feature_limits(
    org_id: str,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    return _dispatch(
        state,
        "feature_limits",
        {"org_id": org_id, "actor_user_id": _actor(auth)},
    )


@router.post("/saas/coupon")
def upsert_coupon(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "upsert_coupon", payload)


@router.post("/saas/checkout")
def checkout(
    body: SaasPayload,
    state: ApiState = Depends(get_api_state),
    auth: dict[str, Any] = Depends(require_authenticated_actor),
) -> JSONResponse:
    payload = _with_actor(auth, body.model_dump(exclude_none=True))
    return _dispatch(state, "checkout", payload)
