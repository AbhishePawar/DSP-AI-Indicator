"""RC1 Milestone 11 — thin Super Admin Control Center routes under /admin/*.

Additive to A010 institutional_admin. Configuration registry + façades only.
Never executes valuation / AI / risk engines. Requires admin access.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.dependencies import ApiState, get_api_state, require_admin_access
from api_platform.api.production_ops_wiring import build_production_ops_deps

router = APIRouter(
    tags=["control-center"],
    dependencies=[Depends(require_admin_access)],
)


class ControlCenterPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    module_id: str | None = Field(None, max_length=64)
    configuration: dict[str, Any] | None = None
    patch: dict[str, Any] | None = None
    author: str | None = Field(None, max_length=128)
    actor_user_id: str | None = Field(None, max_length=128)
    reason: str | None = Field(None, max_length=512)
    approval_status: str | None = Field(None, max_length=32)
    replace: bool | None = None
    version: int | None = Field(None, ge=0, le=10_000_000)
    limit: int | None = Field(None, ge=1, le=500)
    flags: dict[str, Any] | None = None
    flag: str | None = Field(None, max_length=128)
    enabled: bool | None = None
    page_id: str | None = Field(None, max_length=64)
    title: str | None = Field(None, max_length=256)
    body: str | None = None
    published: bool | None = None
    rule_id: str | None = Field(None, max_length=128)
    name: str | None = Field(None, max_length=256)
    category: str | None = Field(None, max_length=64)
    condition: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    backup_action: str | None = Field(None, max_length=32)
    snapshot_id: str | None = Field(None, max_length=128)
    label: str | None = Field(None, max_length=128)
    org_id: str | None = Field(None, max_length=128)


def _author(
    body: ControlCenterPayload | None,
    x_user_id: str | None,
) -> str:
    if body and body.author:
        return body.author
    if body and body.actor_user_id:
        return body.actor_user_id
    return (x_user_id or "").strip() or "admin"


def _dispatch(
    state: ApiState,
    action: str,
    payload: dict[str, Any] | None = None,
) -> JSONResponse:
    try:
        result = state.platform.run_control_center(
            action,
            api_state=state,
            payload=payload,
            ops_deps=build_production_ops_deps(),
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
    status = 200 if result.get("ok") is not False else 400
    return JSONResponse(status_code=status, content=result)


@router.get("/admin/control-center/schema")
def control_center_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.control_center_schema()}


@router.get("/admin/control-center/dashboard")
def control_center_dashboard(
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dispatch(state, "dashboard")


@router.get("/admin/configuration/registry")
def configuration_registry(
    module_id: str | None = Query(None, max_length=64),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    if module_id:
        return _dispatch(state, "get_module", {"module_id": module_id})
    return _dispatch(state, "get_registry")


@router.post("/admin/configuration")
def update_configuration(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "update_configuration", payload)


@router.get("/admin/configuration/history")
def configuration_history(
    module_id: str | None = Query(None, max_length=64),
    limit: int = Query(50, ge=1, le=500),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dispatch(
        state, "history", {"module_id": module_id, "limit": limit}
    )


@router.post("/admin/rollback")
def rollback_configuration(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "rollback", payload)


@router.post("/admin/branding")
def update_branding(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "branding", payload)


@router.post("/admin/cms")
def update_cms(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "cms", payload)


@router.post("/admin/feature-flags/overrides")
def update_feature_flags(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "feature_flags", payload)


@router.post("/admin/valuation/config")
def update_valuation_config(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "valuation", payload)


@router.post("/admin/ai/config")
def update_ai_config(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "ai", payload)


@router.post("/admin/risk/config")
def update_risk_config(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "risk", payload)


@router.post("/admin/market/config")
def update_market_config(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "market", payload)


@router.post("/admin/connectors/config")
def update_connectors_config(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "connectors", payload)


@router.get("/admin/business-rules")
def list_business_rules(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "business_rules_list")


@router.post("/admin/business-rules")
def upsert_business_rule(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "business_rules_upsert", payload)


@router.delete("/admin/business-rules/{rule_id}")
def delete_business_rule(
    rule_id: str,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dispatch(
        state,
        "business_rules_delete",
        {"rule_id": rule_id, "author": (x_user_id or "").strip() or "admin"},
    )


@router.post("/admin/notifications/config")
def update_notifications(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "notifications", payload)


@router.post("/admin/dashboard/layout")
def update_dashboard_layout(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "dashboard_layout", payload)


@router.post("/admin/security/config")
def update_security_config(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "security", payload)


@router.post("/admin/templates/config")
def update_templates(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "templates", payload)


@router.post("/admin/saas/control")
def saas_control(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "saas_control", payload)


@router.get("/admin/monitoring")
def monitoring_center(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "monitoring")


@router.post("/admin/backup/control")
def backup_control(
    body: ControlCenterPayload,
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    payload = body.model_dump(exclude_none=True)
    payload["author"] = _author(body, x_user_id)
    return _dispatch(state, "backup", payload)


@router.get("/admin/release")
def release_center(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "release")


@router.get("/admin/audit/config")
def config_audit(
    limit: int = Query(200, ge=1, le=500),
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dispatch(state, "audit", {"limit": limit})


@router.get("/admin/users-orgs")
def users_orgs_control(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "users_orgs")
