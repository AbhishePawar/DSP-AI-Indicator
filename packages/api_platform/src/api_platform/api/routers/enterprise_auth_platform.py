"""Enterprise multi-provider authentication API (extends A009 + EPIC-016 cookies)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api_platform.api.dependencies import ApiState, get_api_state

router = APIRouter(tags=["auth-enterprise"])


def _platform():
    from auth.enterprise_platform import get_enterprise_auth_platform

    return get_enterprise_auth_platform()


def _attach_auth_cookies(
    response: JSONResponse,
    result: dict[str, Any],
    *,
    remember_me: bool = False,
) -> JSONResponse:
    try:
        from security_platform.security.cookies import cookie_auth_enabled, set_auth_cookies

        if not cookie_auth_enabled():
            return response
        tokens = result.get("tokens") or {}
        access = tokens.get("access_token")
        if not access:
            return response
        csrf = set_auth_cookies(
            response,
            access_token=str(access),
            refresh_token=tokens.get("refresh_token"),
            session_id=tokens.get("session_id")
            or (result.get("session") or {}).get("session_id"),
            remember_me=remember_me,
        )
        body = {
            "ok": True,
            "result": {**result, "csrf_token": csrf, "cookie_auth": True},
            "message": None,
        }
        out = JSONResponse(content=body)
        set_auth_cookies(
            out,
            access_token=str(access),
            refresh_token=tokens.get("refresh_token"),
            session_id=tokens.get("session_id")
            or (result.get("session") or {}).get("session_id"),
            remember_me=remember_me,
            csrf_token=csrf,
        )
        return out
    except Exception:  # noqa: BLE001
        return response


def _err(exc: Exception, status: int = 400) -> JSONResponse:
    msg = str(exc)
    if "credential" in msg.lower() or "invalid otp" in msg.lower() or "expired" in msg.lower():
        status = 401 if status == 400 else status
    if "rate limit" in msg.lower() or "too many" in msg.lower():
        status = 429
    if "unavailable" in msg.lower() and "oauth" in msg.lower():
        status = 503
    if "administrator" in msg.lower() or "permission" in msg.lower():
        status = 403
    return JSONResponse(
        status_code=status,
        content={"ok": False, "error": msg, "message": "Data unavailable."},
    )


def _client_meta(request: Request) -> dict[str, str | None]:
    return {
        "ip_hint": request.client.host if request.client else None,
        "user_agent_hint": request.headers.get("user-agent"),
    }


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=256)
    password: str = Field(..., min_length=8, max_length=256)
    confirm_password: str = Field(..., min_length=8, max_length=256)
    username: str | None = Field(None, max_length=64)


class LoginPasswordRequest(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=256)
    password: str = Field(..., min_length=1, max_length=256)
    remember_me: bool = False
    # Backward-compatible aliases
    username: str | None = None
    email: str | None = None


class PasswordResetRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=256)


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=8, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=256)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=256)
    new_password: str = Field(..., min_length=8, max_length=256)


class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=8, max_length=256)


class OAuthBeginRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)
    redirect_uri: str = Field(..., min_length=8, max_length=512)
    state: str | None = None


class OAuthCallbackRequest(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)
    code: str = Field(..., min_length=1, max_length=2048)
    state: str | None = None
    redirect_uri: str = Field(..., min_length=8, max_length=512)
    remember_me: bool = False


class OtpRequest(BaseModel):
    mobile: str = Field(..., min_length=10, max_length=20)


class OtpVerifyRequest(BaseModel):
    challenge_id: str = Field(..., min_length=8, max_length=128)
    code: str = Field(..., min_length=4, max_length=8)
    remember_me: bool = False
    name: str | None = Field(None, max_length=128)


class MagicLinkRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=256)


class MagicLinkConsume(BaseModel):
    token: str = Field(..., min_length=8, max_length=256)
    remember_me: bool = False


class AccessRequestBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=256)
    organization: str = Field("", max_length=256)
    reason: str = Field("", max_length=2000)


class AccessDecisionBody(BaseModel):
    approve: bool
    notes: str | None = Field(None, max_length=2000)
    role: str = Field("enterprise_client", max_length=64)


class InvitationAcceptBody(BaseModel):
    token: str = Field(..., min_length=8, max_length=256)
    password: str = Field(..., min_length=8, max_length=256)
    confirm_password: str = Field(..., min_length=8, max_length=256)
    username: str | None = Field(None, max_length=64)


class AdminStatusBody(BaseModel):
    active: bool


class AdminResetPasswordBody(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=256)


class AdminRolesBody(BaseModel):
    roles: list[str] = Field(..., min_length=1)


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ValueError("Authorization Bearer token required")
    return authorization.split(" ", 1)[1].strip()


@router.get("/auth/enterprise/schema")
def enterprise_schema() -> dict[str, Any]:
    return {"ok": True, "schema": _platform().schema()}


@router.get("/auth/enterprise/providers")
def enterprise_providers() -> dict[str, Any]:
    return {"ok": True, "result": _platform().provider_status()}


@router.post("/auth/enterprise/register")
def enterprise_register(body: RegisterRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().register_email(
            name=body.name,
            email=body.email,
            password=body.password,
            confirm_password=body.confirm_password,
            username=body.username,
            ip_hint=meta["ip_hint"],
        )
        return JSONResponse({"ok": True, "result": result, "message": None})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/verify-email")
def enterprise_verify_email(body: VerifyEmailRequest) -> JSONResponse:
    try:
        return JSONResponse({"ok": True, "result": _platform().verify_email(body.token)})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/login")
def enterprise_login(body: LoginPasswordRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        identifier = body.identifier or body.username or body.email or ""
        result = _platform().login_password(
            identifier=identifier,
            password=body.password,
            remember_me=body.remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        response = JSONResponse({"ok": True, "result": result, "message": None})
        return _attach_auth_cookies(response, result, remember_me=body.remember_me)
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=401)


@router.post("/auth/enterprise/password/forgot")
def enterprise_forgot(body: PasswordResetRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().request_password_reset(body.email, ip_hint=meta["ip_hint"])
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/password/reset")
def enterprise_reset(body: PasswordResetConfirm) -> JSONResponse:
    try:
        result = _platform().confirm_password_reset(body.token, body.new_password)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/password/change")
def enterprise_change_password(
    body: ChangePasswordRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().change_password(
            user_id=str(user["user_id"]),
            current_password=body.current_password,
            new_password=body.new_password,
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/oauth/begin")
def enterprise_oauth_begin(body: OAuthBeginRequest) -> JSONResponse:
    try:
        result = _platform().oauth_begin(
            body.provider, redirect_uri=body.redirect_uri, state=body.state
        )
        status = 200 if result.get("available") else 503
        return JSONResponse({"ok": bool(result.get("available")), "result": result}, status_code=status)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/oauth/callback")
def enterprise_oauth_callback(body: OAuthCallbackRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().oauth_callback(
            body.provider,
            code=body.code,
            state=body.state,
            redirect_uri=body.redirect_uri,
            remember_me=body.remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        response = JSONResponse({"ok": True, "result": result, "message": None})
        return _attach_auth_cookies(response, result, remember_me=body.remember_me)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/otp/request")
def enterprise_otp_request(body: OtpRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().request_mobile_otp(body.mobile, ip_hint=meta["ip_hint"])
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/otp/verify")
def enterprise_otp_verify(body: OtpVerifyRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().verify_mobile_otp(
            challenge_id=body.challenge_id,
            code=body.code,
            remember_me=body.remember_me,
            name=body.name,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        response = JSONResponse({"ok": True, "result": result, "message": None})
        return _attach_auth_cookies(response, result, remember_me=body.remember_me)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/magic-link/request")
def enterprise_magic_request(body: MagicLinkRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().request_magic_link(body.email, ip_hint=meta["ip_hint"])
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/magic-link/consume")
def enterprise_magic_consume(body: MagicLinkConsume, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().consume_magic_link(
            body.token,
            remember_me=body.remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        response = JSONResponse({"ok": True, "result": result, "message": None})
        return _attach_auth_cookies(response, result, remember_me=body.remember_me)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/access-requests")
def enterprise_access_submit(body: AccessRequestBody) -> JSONResponse:
    try:
        result = _platform().submit_access_request(
            name=body.name,
            email=body.email,
            organization=body.organization,
            reason=body.reason,
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/enterprise/access-requests")
def enterprise_access_list(
    status: str | None = None,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        result = _platform().list_access_requests(status=status)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/access-requests/{request_id}/decide")
def enterprise_access_decide(
    request_id: str,
    body: AccessDecisionBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        actor = _platform().require_admin(token)
        result = _platform().decide_access_request(
            request_id,
            approve=body.approve,
            actor_user_id=str(actor["user_id"]),
            notes=body.notes,
            role=body.role,
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/invitations/accept")
def enterprise_invite_accept(body: InvitationAcceptBody) -> JSONResponse:
    try:
        result = _platform().accept_invitation(
            token=body.token,
            password=body.password,
            confirm_password=body.confirm_password,
            username=body.username,
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/enterprise/admin/users")
def enterprise_admin_users(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        return JSONResponse({"ok": True, "result": _platform().admin_list_users()})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/admin/users/{user_id}/status")
def enterprise_admin_status(
    user_id: str,
    body: AdminStatusBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        result = _platform().admin_set_status(user_id, active=body.active)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/admin/users/{user_id}/reset-password")
def enterprise_admin_reset(
    user_id: str,
    body: AdminResetPasswordBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        result = _platform().admin_reset_password(user_id, body.new_password)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.put("/auth/enterprise/admin/users/{user_id}/roles")
def enterprise_admin_roles(
    user_id: str,
    body: AdminRolesBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        actor = _platform().require_admin(token)
        result = _platform().admin_assign_roles(
            user_id,
            body.roles,
            actor_roles=list(actor.get("roles") or []),
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/enterprise/admin/login-history")
def enterprise_login_history(
    user_id: str | None = None,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        result = _platform().login_history(user_id=user_id)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/enterprise/admin/sessions")
def enterprise_sessions(
    user_id: str | None = None,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        result = _platform().list_active_sessions(user_id=user_id)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/enterprise/password/strength")
def enterprise_password_strength(password: str) -> dict[str, Any]:
    from auth.enterprise_platform import password_strength

    return {"ok": True, "result": password_strength(password)}


# --- Plan aliases (/auth/*) + account / MFA reserved / admin extras ---------


@router.get("/auth/providers")
def auth_providers_alias() -> dict[str, Any]:
    return {"ok": True, "result": _platform().provider_status()}


@router.post("/auth/register")
def auth_register_alias(body: RegisterRequest, request: Request) -> JSONResponse:
    return enterprise_register(body, request)


@router.post("/auth/verify-email")
def auth_verify_email_alias(body: VerifyEmailRequest) -> JSONResponse:
    return enterprise_verify_email(body)


@router.post("/auth/forgot-password")
def auth_forgot_alias(body: PasswordResetRequest, request: Request) -> JSONResponse:
    return enterprise_forgot(body, request)


@router.post("/auth/reset-password")
def auth_reset_alias(body: PasswordResetConfirm) -> JSONResponse:
    return enterprise_reset(body)


@router.post("/auth/otp/request")
def auth_otp_request_alias(body: OtpRequest, request: Request) -> JSONResponse:
    return enterprise_otp_request(body, request)


@router.post("/auth/otp/verify")
def auth_otp_verify_alias(body: OtpVerifyRequest, request: Request) -> JSONResponse:
    return enterprise_otp_verify(body, request)


@router.post("/auth/otp/resend")
def auth_otp_resend(body: OtpRequest, request: Request) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().resend_mobile_otp(body.mobile, ip_hint=meta["ip_hint"])
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/oauth/{provider}/start")
def auth_oauth_start(
    provider: str,
    redirect_uri: str,
    next: str | None = None,
    state: str | None = None,
) -> JSONResponse:
    _ = next
    try:
        result = _platform().oauth_begin(provider, redirect_uri=redirect_uri, state=state)
        status = 200 if result.get("available") else 503
        return JSONResponse(
            {"ok": bool(result.get("available")), "result": result},
            status_code=status,
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/oauth/{provider}/callback")
def auth_oauth_callback_get(
    provider: str,
    request: Request,
    code: str,
    redirect_uri: str,
    state: str | None = None,
    remember_me: bool = False,
) -> JSONResponse:
    try:
        meta = _client_meta(request)
        result = _platform().oauth_callback(
            provider,
            code=code,
            state=state,
            redirect_uri=redirect_uri,
            remember_me=remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        response = JSONResponse({"ok": True, "result": result, "message": None})
        return _attach_auth_cookies(response, result, remember_me=remember_me)
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


class ProfilePatchBody(BaseModel):
    name: str | None = Field(None, max_length=128)
    avatar: str | None = Field(None, max_length=1024)


class ChangeEmailBody(BaseModel):
    new_email: str = Field(..., min_length=3, max_length=256)


class ConfirmEmailChangeBody(BaseModel):
    token: str = Field(..., min_length=8, max_length=256)


class UnlinkProviderBody(BaseModel):
    provider: str = Field(..., min_length=2, max_length=32)


class TrustDeviceBody(BaseModel):
    trusted: bool = True


class ProvisionUserBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    email: str = Field(..., min_length=3, max_length=256)
    username: str | None = Field(None, max_length=64)
    password: str | None = Field(None, max_length=256)
    roles: list[str] = Field(default_factory=lambda: ["read_only"])


@router.get("/auth/me")
def auth_me(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {"ok": True, "result": _platform().get_profile(str(user["user_id"]))}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.patch("/auth/me")
def auth_me_patch(
    body: ProfilePatchBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().update_profile(
            str(user["user_id"]), name=body.name, avatar=body.avatar
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/me/change-password")
def auth_me_change_password(
    body: ChangePasswordRequest,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    return enterprise_change_password(body, authorization)


@router.post("/auth/me/change-email")
def auth_me_change_email(
    body: ChangeEmailBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().change_email(str(user["user_id"]), body.new_email)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/me/confirm-change-email")
def auth_me_confirm_change_email(body: ConfirmEmailChangeBody) -> JSONResponse:
    try:
        return JSONResponse(
            {"ok": True, "result": _platform().confirm_change_email(body.token)}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.delete("/auth/me")
def auth_me_delete(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {"ok": True, "result": _platform().delete_account(str(user["user_id"]))}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/me/providers/unlink")
def auth_unlink_provider(
    body: UnlinkProviderBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().unlink_provider(str(user["user_id"]), body.provider)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/me/devices")
def auth_my_devices(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {"ok": True, "result": _platform().list_my_devices(str(user["user_id"]))}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.delete("/auth/me/devices/{device_id}")
def auth_revoke_device(
    device_id: str,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {
                "ok": True,
                "result": _platform().revoke_device(str(user["user_id"]), device_id),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/me/devices/{device_id}/trust")
def auth_trust_device(
    device_id: str,
    body: TrustDeviceBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {
                "ok": True,
                "result": _platform().trust_device(
                    str(user["user_id"]), device_id, trusted=body.trusted
                ),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/me/login-history")
def auth_my_login_history(
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {
                "ok": True,
                "result": _platform().my_login_history(str(user["user_id"])),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/me/sessions/revoke-all")
def auth_revoke_my_sessions(
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {
                "ok": True,
                "result": _platform().revoke_sessions_for_user(str(user["user_id"])),
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


def _mfa_reserved() -> JSONResponse:
    status = _platform().mfa.status()
    return JSONResponse(
        {
            "ok": False,
            "error": "MFA not enabled",
            "result": status,
            "message": status.get("message"),
        },
        status_code=501,
    )


@router.post("/auth/mfa/totp/enroll")
def auth_mfa_totp_enroll() -> JSONResponse:
    return _mfa_reserved()


@router.post("/auth/mfa/totp/verify")
def auth_mfa_totp_verify() -> JSONResponse:
    return _mfa_reserved()


@router.post("/auth/mfa/webauthn/register")
def auth_mfa_webauthn_register() -> JSONResponse:
    return _mfa_reserved()


@router.post("/auth/mfa/webauthn/authenticate")
def auth_mfa_webauthn_authenticate() -> JSONResponse:
    return _mfa_reserved()


@router.post("/auth/enterprise/admin/users/provision")
def enterprise_admin_provision(
    body: ProvisionUserBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        actor = _platform().require_admin(token)
        result = _platform().admin_provision_user(
            name=body.name,
            email=body.email,
            username=body.username,
            password=body.password,
            roles=body.roles,
            actor_roles=list(actor.get("roles") or []),
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/admin/users/{user_id}/unlock")
def enterprise_admin_unlock(
    user_id: str,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        return JSONResponse(
            {"ok": True, "result": _platform().admin_unlock_user(user_id)}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/enterprise/admin/users/{user_id}/revoke-sessions")
def enterprise_admin_revoke_sessions(
    user_id: str,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        _platform().require_admin(token)
        return JSONResponse(
            {"ok": True, "result": _platform().admin_revoke_sessions(user_id)}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


# Silence unused import when state wiring not needed for platform singleton.
_ = (ApiState, get_api_state, Depends)
