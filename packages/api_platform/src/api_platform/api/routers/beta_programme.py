"""P5.1 — Closed Beta programme HTTP surface (ops only, additive).

Does not modify analyse / valuation / recommendation contracts.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from admin.beta_programme import get_beta_programme
from api_platform.api.dependencies import require_admin_access

public_router = APIRouter(tags=["beta"])
admin_router = APIRouter(
    tags=["admin-beta"],
    dependencies=[Depends(require_admin_access)],
)


def _err(exc: Exception, status: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": str(exc), "message": "Data unavailable."},
    )


def _actor_from_authorization(authorization: str | None) -> str:
    if not authorization:
        return "anonymous"
    # Do not log raw tokens — hash-length fingerprint only
    return f"bearer:{len(authorization)}"


class FeedbackBody(BaseModel):
    category: str = Field(default="general_comments", max_length=64)
    severity: str = Field(default="medium", max_length=32)
    title: str = Field(..., min_length=1, max_length=160)
    description: str = Field(..., min_length=1, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)
    screenshot_note: str | None = Field(default=None, max_length=200)
    app_version: str | None = Field(default=None, max_length=32)
    browser: str | None = Field(default=None, max_length=200)
    company_analysed: str | None = Field(default=None, max_length=16)
    page_path: str | None = Field(default="/", max_length=120)
    acknowledgement: bool = True


class InviteBody(BaseModel):
    email_or_username: str = Field(..., min_length=1, max_length=256)
    role: str = Field(default="beta_participant", max_length=64)
    status: str = Field(default="pending", max_length=32)


class InviteStatusBody(BaseModel):
    status: str = Field(..., max_length=32)


class IssuePatchBody(BaseModel):
    status: str | None = Field(default=None, max_length=32)
    severity: str | None = Field(default=None, max_length=32)
    priority: str | None = Field(default=None, max_length=8)
    resolution: str | None = Field(default=None, max_length=500)


class ConfigPatchBody(BaseModel):
    closed_beta_mode: bool | None = None
    beta_feature_flag: bool | None = None
    invitation_only: bool | None = None
    banner_enabled: bool | None = None
    banner_text: str | None = Field(default=None, max_length=240)
    expiry_at: str | None = Field(default=None, max_length=64)
    read_only_safeguards: bool | None = None


class AnalyticsEventBody(BaseModel):
    kind: str = Field(..., max_length=64)
    ok: bool = True
    duration_ms: int = Field(default=0, ge=0, le=600_000)
    feature: str | None = Field(default=None, max_length=64)


class AccessCheckBody(BaseModel):
    identity: str | None = Field(default=None, max_length=256)
    is_admin: bool = False


@public_router.get("/beta/status")
def beta_status(
    identity: str | None = Query(default=None, max_length=256),
    is_admin: bool = Query(default=False),
) -> dict[str, Any]:
    store = get_beta_programme()
    cfg = store.get_config()
    allowed = store.is_identity_allowed(identity, is_admin=is_admin)
    return {
        "ok": True,
        "result": {
            "programme": cfg,
            "access_allowed": allowed,
            "feature_flag": cfg.get("beta_feature_flag"),
            "banner": {
                "enabled": bool(cfg.get("banner_enabled")),
                "text": cfg.get("banner_text"),
            },
        },
    }


@public_router.post("/beta/access-check")
def beta_access_check(body: AccessCheckBody) -> dict[str, Any]:
    store = get_beta_programme()
    allowed = store.is_identity_allowed(body.identity, is_admin=body.is_admin)
    return {"ok": True, "result": {"access_allowed": allowed}}


@public_router.post("/beta/feedback")
def beta_feedback(
    body: FeedbackBody,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    if not body.acknowledgement:
        return _err(ValueError("acknowledgement required"), 400)
    store = get_beta_programme()
    actor = _actor_from_authorization(authorization)
    record = store.submit_feedback(body.model_dump(), actor=actor)
    return {"ok": True, "result": record}


@public_router.post("/beta/analytics/event")
def beta_analytics_event(
    body: AnalyticsEventBody,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    store = get_beta_programme()
    actor = _actor_from_authorization(authorization)
    record = store.record_analytics_event(body.model_dump(), actor=actor)
    return {"ok": True, "result": record}


@admin_router.get("/admin/beta/dashboard")
def admin_beta_dashboard() -> dict[str, Any]:
    store = get_beta_programme()
    return {"ok": True, "result": store.dashboard()}


@admin_router.get("/admin/beta/config")
def admin_beta_config() -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().get_config()}


@admin_router.put("/admin/beta/config")
def admin_beta_config_put(body: ConfigPatchBody) -> dict[str, Any]:
    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    result = get_beta_programme().update_config(patch, actor="admin")
    return {"ok": True, "result": result}


@admin_router.get("/admin/beta/invites")
def admin_beta_invites() -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().list_invites()}


@admin_router.post("/admin/beta/invites")
def admin_beta_invites_create(body: InviteBody) -> Any:
    try:
        record = get_beta_programme().upsert_invite(
            email_or_username=body.email_or_username,
            role=body.role,
            status=body.status,
            actor="admin",
        )
        return {"ok": True, "result": record}
    except ValueError as exc:
        return _err(exc)


@admin_router.patch("/admin/beta/invites/{invite_id}")
def admin_beta_invite_status(invite_id: str, body: InviteStatusBody) -> Any:
    try:
        record = get_beta_programme().set_invite_status(
            invite_id, body.status, actor="admin"
        )
        if record is None:
            return _err(LookupError("invite not found"), 404)
        return {"ok": True, "result": record}
    except ValueError as exc:
        return _err(exc)


@admin_router.get("/admin/beta/feedback")
def admin_beta_feedback() -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().list_feedback()}


@admin_router.get("/admin/beta/issues")
def admin_beta_issues() -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().list_issues()}


@admin_router.patch("/admin/beta/issues/{issue_id}")
def admin_beta_issue_patch(issue_id: str, body: IssuePatchBody) -> Any:
    try:
        record = get_beta_programme().update_issue(
            issue_id,
            status=body.status,
            severity=body.severity,
            priority=body.priority,
            resolution=body.resolution,
            actor="admin",
        )
        if record is None:
            return _err(LookupError("issue not found"), 404)
        return {"ok": True, "result": record}
    except ValueError as exc:
        return _err(exc)


@admin_router.get("/admin/beta/analytics")
def admin_beta_analytics() -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().analytics_summary()}


@admin_router.get("/admin/beta/audit")
def admin_beta_audit(limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().list_audit(limit=limit)}


@admin_router.get("/admin/beta/snapshot")
def admin_beta_snapshot() -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().export_snapshot()}


class SnapshotImportBody(BaseModel):
    snapshot: dict[str, Any]
    merge: bool = False


@admin_router.post("/admin/beta/snapshot/import")
def admin_beta_snapshot_import(body: SnapshotImportBody) -> Any:
    try:
        result = get_beta_programme().import_snapshot(
            body.snapshot, actor="admin", merge=body.merge
        )
        return {"ok": True, "result": result}
    except ValueError as exc:
        return _err(exc)


class IssueClassifyBody(BaseModel):
    disposition: str = Field(..., max_length=32)
    rationale: str = Field(..., min_length=1, max_length=500)


@admin_router.post("/admin/beta/issues/{issue_id}/classify")
def admin_beta_issue_classify(issue_id: str, body: IssueClassifyBody) -> Any:
    try:
        record = get_beta_programme().classify_issue(
            issue_id,
            disposition=body.disposition,
            rationale=body.rationale,
            actor="admin",
        )
        if record is None:
            return _err(LookupError("issue not found"), 404)
        return {"ok": True, "result": record}
    except ValueError as exc:
        return _err(exc)


@admin_router.get("/admin/beta/rc-assessment")
def admin_beta_rc_assessment() -> dict[str, Any]:
    return {"ok": True, "result": get_beta_programme().rc_assessment()}
