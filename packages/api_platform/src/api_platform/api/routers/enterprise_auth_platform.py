"""Enterprise multi-provider authentication API (extends A009 + EPIC-016 cookies)."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
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
        from security_platform import cookie_auth_enabled, set_auth_cookies

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


def _attach_cookies_to_redirect(
    response: RedirectResponse,
    result: dict[str, Any],
    *,
    remember_me: bool = False,
) -> RedirectResponse:
    """Set the same HttpOnly auth cookies as `_attach_auth_cookies`, but on a
    redirect response in place — used by the browser-navigable
    `/auth/microsoft` classic-redirect OAuth flow, which cannot return a
    JSON body since the browser is following a Location header.
    """
    try:
        from security_platform import cookie_auth_enabled, set_auth_cookies

        if not cookie_auth_enabled():
            return response
        tokens = result.get("tokens") or {}
        access = tokens.get("access_token")
        if not access:
            return response
        set_auth_cookies(
            response,
            access_token=str(access),
            refresh_token=tokens.get("refresh_token"),
            session_id=tokens.get("session_id")
            or (result.get("session") or {}).get("session_id"),
            remember_me=remember_me,
        )
    except Exception:  # noqa: BLE001
        pass
    return response


def _provider_redirect_uri(provider: str, redirect_uri: str | None) -> str:
    """Resolve the redirect URI for classic browser-navigable OAuth routes.

    The generic JSON OAuth API (`/auth/enterprise/oauth/*`) always requires
    the caller (SPA) to supply its own `redirect_uri` — that contract is
    unchanged. These provider-specific routes additionally accept a
    server-configured default (`DSP_<PROVIDER>_REDIRECT_URI`) so a plain
    browser navigation to `/auth/microsoft` works without query params.
    """
    if redirect_uri:
        return redirect_uri
    env_key = f"DSP_{provider.upper()}_REDIRECT_URI"
    configured = (os.environ.get(env_key) or "").strip()
    if not configured:
        raise ValueError(
            f"{provider.title()} OAuth unavailable — {env_key} is not configured."
        )
    return configured


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


class OAuthLinkRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=2048)
    state: str | None = None
    redirect_uri: str | None = Field(None, max_length=512)


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


def _oauth_frontend_url() -> str:
    return (os.environ.get("DSP_FRONTEND_URL") or "http://localhost:3000").rstrip("/")


@router.get("/auth/microsoft")
def auth_microsoft_start(
    redirect_uri: str | None = None,
    state: str | None = None,
) -> Response:
    """Classic browser-navigable Microsoft Entra ID login start.

    Thin convenience wrapper around the existing generic
    `oauth_begin("MICROSOFT", ...)` platform method — no OAuth logic is
    duplicated here. The SPA popup flow (`/auth/enterprise/oauth/begin`,
    `/auth/oauth/{provider}/start`) is unchanged.
    """
    try:
        uri = _provider_redirect_uri("MICROSOFT", redirect_uri)
        result = _platform().oauth_begin("MICROSOFT", redirect_uri=uri, state=state)
        if not result.get("available"):
            return _err(
                RuntimeError(result.get("message") or "Microsoft OAuth unavailable."),
                status=503,
            )
        return RedirectResponse(result["authorization_url"], status_code=302)
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=503)


@router.get("/auth/microsoft/callback")
def auth_microsoft_callback(
    request: Request,
    code: str,
    state: str | None = None,
    redirect_uri: str | None = None,
    remember_me: bool = False,
) -> Response:
    """Classic browser-navigable Microsoft Entra ID callback.

    Delegates entirely to `EnterpriseAuthPlatform.oauth_callback`, which
    performs PKCE verification, JWKS/ID-token validation, nonce checking and
    account linking/provisioning identically to Google. Establishes a
    session via HttpOnly cookies and redirects back into the (unchanged)
    frontend, matching how the existing JSON callback attaches cookies.
    """
    frontend = _oauth_frontend_url()
    try:
        uri = _provider_redirect_uri("MICROSOFT", redirect_uri)
        meta = _client_meta(request)
        result = _platform().oauth_callback(
            "MICROSOFT",
            code=code,
            state=state,
            redirect_uri=uri,
            remember_me=remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        redirect = RedirectResponse(f"{frontend}/dashboard", status_code=302)
        return _attach_cookies_to_redirect(redirect, result, remember_me=remember_me)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(
            f"{frontend}/login?error={quote(str(exc))}&provider=microsoft",
            status_code=302,
        )


@router.post("/auth/microsoft/link")
def auth_microsoft_link(
    body: OAuthLinkRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Link a Microsoft Entra ID / personal account to the signed-in user.

    Distinct from `oauth_callback` (sign-in): this binds the verified OAuth
    identity to the *currently authenticated* user rather than matching by
    email or auto-provisioning, and rejects the link if the Microsoft
    identity already belongs to a different account.
    """
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        meta = _client_meta(request)
        uri = _provider_redirect_uri("MICROSOFT", body.redirect_uri)
        result = _platform().link_oauth_provider(
            str(user["user_id"]),
            "MICROSOFT",
            code=body.code,
            state=body.state,
            redirect_uri=uri,
            ip_hint=meta["ip_hint"],
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/microsoft/unlink")
def auth_microsoft_unlink(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().unlink_provider(str(user["user_id"]), "MICROSOFT")
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/facebook")
def auth_facebook_start(
    redirect_uri: str | None = None,
    state: str | None = None,
) -> Response:
    """Classic browser-navigable Facebook Login start.

    Thin convenience wrapper around the existing generic
    `oauth_begin("FACEBOOK", ...)` platform method — the same
    `OAuthProviderAdapter` used for Google/Microsoft; no OAuth logic is
    duplicated here. The SPA popup flow (`/auth/enterprise/oauth/begin`,
    `/auth/oauth/{provider}/start`) is unchanged.
    """
    try:
        uri = _provider_redirect_uri("FACEBOOK", redirect_uri)
        result = _platform().oauth_begin("FACEBOOK", redirect_uri=uri, state=state)
        if not result.get("available"):
            return _err(
                RuntimeError(result.get("message") or "Facebook OAuth unavailable."),
                status=503,
            )
        return RedirectResponse(result["authorization_url"], status_code=302)
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=503)


@router.get("/auth/facebook/callback")
def auth_facebook_callback(
    request: Request,
    code: str,
    state: str | None = None,
    redirect_uri: str | None = None,
    remember_me: bool = False,
) -> Response:
    """Classic browser-navigable Facebook Login callback.

    Delegates entirely to `EnterpriseAuthPlatform.oauth_callback`, which
    performs the authorization-code exchange, live Graph `/me` profile
    retrieval, and account linking/provisioning identically to Google and
    Microsoft. Establishes a session via HttpOnly cookies and redirects
    back into the (unchanged) frontend.
    """
    frontend = _oauth_frontend_url()
    try:
        uri = _provider_redirect_uri("FACEBOOK", redirect_uri)
        meta = _client_meta(request)
        result = _platform().oauth_callback(
            "FACEBOOK",
            code=code,
            state=state,
            redirect_uri=uri,
            remember_me=remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        redirect = RedirectResponse(f"{frontend}/dashboard", status_code=302)
        return _attach_cookies_to_redirect(redirect, result, remember_me=remember_me)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(
            f"{frontend}/login?error={quote(str(exc))}&provider=facebook",
            status_code=302,
        )


@router.post("/auth/facebook/link")
def auth_facebook_link(
    body: OAuthLinkRequest,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Link a Facebook account to the signed-in user.

    Distinct from `oauth_callback` (sign-in): this binds the verified OAuth
    identity to the *currently authenticated* user rather than matching by
    email or auto-provisioning, and rejects the link if the Facebook
    identity (or its email) already belongs to a different account.
    """
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        meta = _client_meta(request)
        uri = _provider_redirect_uri("FACEBOOK", body.redirect_uri)
        result = _platform().link_oauth_provider(
            str(user["user_id"]),
            "FACEBOOK",
            code=body.code,
            state=body.state,
            redirect_uri=uri,
            ip_hint=meta["ip_hint"],
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/facebook/unlink")
def auth_facebook_unlink(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().unlink_provider(str(user["user_id"]), "FACEBOOK")
        return JSONResponse({"ok": True, "result": result})
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


class TotpVerifyBody(BaseModel):
    mfa_token: str = Field(..., min_length=8, max_length=2048)
    code: str | None = Field(None, min_length=6, max_length=8)
    recovery_code: str | None = Field(None, min_length=8, max_length=32)
    remember_device: bool = False
    device_id: str | None = None


class TotpEnrollConfirmBody(BaseModel):
    code: str = Field(..., min_length=6, max_length=8)


class TotpDisableBody(BaseModel):
    current_password: str | None = Field(None, max_length=256)


class MfaDisableBody(BaseModel):
    """Same as :class:`TotpDisableBody` but forces re-authentication.

    The canonical ``/auth/mfa/disable`` route requires the current password
    (unlike the legacy ``/auth/mfa/totp/disable`` alias, kept optional for
    backward compatibility) so a hijacked access token alone can never
    disable a second factor.
    """

    current_password: str = Field(..., min_length=1, max_length=256)


class RecoveryCodesRegenerateBody(BaseModel):
    """Regenerating recovery codes is sensitive — force re-authentication."""

    current_password: str = Field(..., min_length=1, max_length=256)


class WebauthnRegisterCompleteBody(BaseModel):
    state: str = Field(..., min_length=8, max_length=256)
    credential: dict[str, Any]
    label: str | None = Field(None, max_length=128)


class WebauthnAuthenticateBeginBody(BaseModel):
    identifier: str | None = Field(None, max_length=256)


class WebauthnAuthenticateCompleteBody(BaseModel):
    state: str = Field(..., min_length=8, max_length=256)
    credential: dict[str, Any]
    remember_me: bool = False


class WebauthnRemoveBody(BaseModel):
    credential_id: str = Field(..., min_length=4, max_length=1024)


@router.post("/auth/mfa/totp/enroll")
def auth_mfa_totp_enroll(
    request: Request, authorization: str | None = Header(default=None)
) -> JSONResponse:
    """Begin TOTP enrollment for the authenticated user.

    Returns 501 (unchanged contract) while ``DSP_AUTH_MFA`` is unset/false.
    """
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().mfa_totp_enroll_begin(
            str(user["user_id"]), ip_hint=_client_meta(request)["ip_hint"]
        )
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _mfa_reserved()
        return _err(exc)


@router.post("/auth/mfa/totp/enroll/confirm")
def auth_mfa_totp_enroll_confirm(
    body: TotpEnrollConfirmBody,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().mfa_totp_enroll_confirm(
            str(user["user_id"]), body.code, ip_hint=_client_meta(request)["ip_hint"]
        )
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=401)


@router.post("/auth/mfa/totp/verify")
def auth_mfa_totp_verify(body: TotpVerifyBody, request: Request) -> JSONResponse:
    """Login-time TOTP step-up — verified against the signed ``mfa_token``.

    The primary session is issued before this step (MFA is additive per the
    platform's documented non-blocking design); this call only confirms the
    step-up factor and optionally marks the current device as trusted.
    """
    try:
        meta = _client_meta(request)
        result = _platform().mfa_totp_verify_stepup(
            mfa_token=body.mfa_token,
            code=body.code,
            recovery_code=body.recovery_code,
            remember_device=body.remember_device,
            device_id=body.device_id,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        if "mfa is disabled" in str(exc).lower():
            return _mfa_reserved()
        return _err(exc, status=401)


@router.post("/auth/mfa/totp/disable")
def auth_mfa_totp_disable(
    body: TotpDisableBody,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().mfa_totp_disable(
            str(user["user_id"]),
            current_password=body.current_password,
            ip_hint=_client_meta(request)["ip_hint"],
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


# -- Canonical short-form MFA routes -------------------------------------
#
# Thin aliases over the exact same platform methods used by `/auth/mfa/totp/*`
# above — no authentication logic is duplicated. `enable` and `disable`
# additionally force re-authentication (mandatory `current_password`) since
# they change the account's second-factor posture.


@router.post("/auth/mfa/enroll")
def auth_mfa_enroll(
    request: Request, authorization: str | None = Header(default=None)
) -> JSONResponse:
    """Begin authenticator-app enrollment (secret + QR + otpauth:// URI)."""
    return auth_mfa_totp_enroll(request, authorization)


@router.post("/auth/mfa/enable")
def auth_mfa_enable(
    body: TotpEnrollConfirmBody,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Confirm the enrollment code and activate TOTP MFA for the account."""
    return auth_mfa_totp_enroll_confirm(body, request, authorization)


@router.post("/auth/mfa/verify")
def auth_mfa_verify(body: TotpVerifyBody, request: Request) -> JSONResponse:
    """Login-time MFA step-up verification (TOTP code or recovery code)."""
    return auth_mfa_totp_verify(body, request)


@router.post("/auth/mfa/disable")
def auth_mfa_disable(
    body: MfaDisableBody,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Disable TOTP MFA. Requires the current password (forced re-auth)."""
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().mfa_totp_disable(
            str(user["user_id"]),
            current_password=body.current_password,
            ip_hint=_client_meta(request)["ip_hint"],
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc, status=401)


@router.get("/auth/mfa/recovery-codes")
def auth_mfa_recovery_codes(authorization: str | None = Header(default=None)) -> JSONResponse:
    """Recovery-code *status* only — counts and last-generated timestamp.

    Codes are salted+hashed at rest; the plaintext values are only ever
    returned once, at generation time (``/auth/mfa/enable`` or
    ``/auth/mfa/recovery-codes/regenerate``).
    """
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().mfa_recovery_codes_status(str(user["user_id"]))
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _mfa_reserved()
        return _err(exc)


@router.post("/auth/mfa/recovery-codes/regenerate")
def auth_mfa_recovery_codes_regenerate(
    body: RecoveryCodesRegenerateBody,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Invalidate existing recovery codes and issue a fresh set (shown once)."""
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().mfa_recovery_codes_regenerate(
            str(user["user_id"]),
            current_password=body.current_password,
            ip_hint=_client_meta(request)["ip_hint"],
        )
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _mfa_reserved()
        return _err(exc, status=401)


@router.post("/auth/mfa/webauthn/register")
def auth_mfa_webauthn_register(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().webauthn_register_begin(str(user["user_id"]))
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _mfa_reserved()
        return _err(exc)


@router.post("/auth/mfa/webauthn/register/complete")
def auth_mfa_webauthn_register_complete(
    body: WebauthnRegisterCompleteBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().webauthn_register_complete(
            str(user["user_id"]),
            {"state": body.state, "credential": body.credential, "label": body.label},
        )
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.get("/auth/mfa/webauthn/credentials")
def auth_mfa_webauthn_credentials(authorization: str | None = Header(default=None)) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {"ok": True, "result": _platform().webauthn_list_credentials(str(user["user_id"]))}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/mfa/webauthn/credentials/remove")
def auth_mfa_webauthn_remove(
    body: WebauthnRemoveBody,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        result = _platform().webauthn_remove_credential(str(user["user_id"]), body.credential_id)
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/mfa/webauthn/authenticate")
def auth_mfa_webauthn_authenticate(body: WebauthnAuthenticateBeginBody | None = None) -> JSONResponse:
    """Begin a discoverable ("usernameless") passkey login or MFA step-up.

    Matches the existing frontend contract exactly (``{identifier?}`` in,
    ``{ok, result}`` out) — no request body is required.
    """
    try:
        identifier = body.identifier if body else None
        result = _platform().webauthn_authenticate_begin(identifier)
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _mfa_reserved()
        return _err(exc)


@router.post("/auth/mfa/webauthn/authenticate/complete")
def auth_mfa_webauthn_authenticate_complete(
    body: WebauthnAuthenticateCompleteBody, request: Request
) -> JSONResponse:
    """Complete a passkey login — establishes a full session like OTP/OAuth."""
    try:
        meta = _client_meta(request)
        result = _platform().webauthn_authenticate_complete(
            {"state": body.state, "credential": body.credential},
            remember_me=body.remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        response = JSONResponse({"ok": True, "result": result, "message": None})
        return _attach_auth_cookies(response, result, remember_me=body.remember_me)
    except NotImplementedError:
        return _mfa_reserved()
    except Exception as exc:  # noqa: BLE001
        if "mfa is disabled" in str(exc).lower():
            return _mfa_reserved()
        return _err(exc, status=401)


def _passkey_reserved() -> JSONResponse:
    """501 response for the passkey routes, worded for passwordless sign-in
    rather than step-up MFA — same underlying `mfa.status()` payload as
    `_mfa_reserved()` (one shared WebAuthn adapter/flag), different wording.
    """
    status = _platform().mfa.status()
    return JSONResponse(
        {
            "ok": False,
            "error": "Passkey authentication not enabled",
            "result": status,
            "message": status.get("message"),
        },
        status_code=501,
    )


@router.post("/auth/passkey/register/begin")
def auth_passkey_register_begin(
    request: Request, authorization: str | None = Header(default=None)
) -> JSONResponse:
    """Begin adding a new passkey to the authenticated user's account.

    Thin wrapper over `EnterpriseAuthPlatform.webauthn_register_begin` — the
    exact method used by `/auth/mfa/webauthn/register`; a credential
    registered here is immediately usable for both MFA step-up and primary
    passwordless sign-in (`/auth/passkey/login/*`), since both share the
    same credential store.
    """
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        meta = _client_meta(request)
        result = _platform().webauthn_register_begin(
            str(user["user_id"]), ip_hint=meta["ip_hint"]
        )
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _passkey_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _passkey_reserved()
        return _err(exc)


@router.post("/auth/passkey/register/complete")
def auth_passkey_register_complete(
    body: WebauthnRegisterCompleteBody,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        meta = _client_meta(request)
        result = _platform().webauthn_register_complete(
            str(user["user_id"]),
            {"state": body.state, "credential": body.credential, "label": body.label},
            ip_hint=meta["ip_hint"],
        )
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _passkey_reserved()
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.post("/auth/passkey/login/begin")
def auth_passkey_login_begin(body: WebauthnAuthenticateBeginBody | None = None) -> JSONResponse:
    """Begin a discoverable ("usernameless") passkey sign-in.

    Identical contract and platform call (`webauthn_authenticate_begin`) as
    `/auth/mfa/webauthn/authenticate` — exposed under `/auth/passkey/*` as
    the dedicated, self-describing primary-login entry point. No request
    body (or `identifier`) is required for a fully passwordless flow.
    """
    try:
        identifier = body.identifier if body else None
        result = _platform().webauthn_authenticate_begin(identifier)
        return JSONResponse({"ok": True, "result": result})
    except NotImplementedError:
        return _passkey_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _passkey_reserved()
        return _err(exc)


@router.post("/auth/passkey/login/complete")
def auth_passkey_login_complete(
    body: WebauthnAuthenticateCompleteBody, request: Request
) -> JSONResponse:
    """Complete passkey sign-in — establishes a full session, same as
    password/OAuth/OTP login (HttpOnly cookies + JWT access/refresh)."""
    try:
        meta = _client_meta(request)
        result = _platform().webauthn_authenticate_complete(
            {"state": body.state, "credential": body.credential},
            remember_me=body.remember_me,
            ip_hint=meta["ip_hint"],
            user_agent_hint=meta["user_agent_hint"],
        )
        response = JSONResponse({"ok": True, "result": result, "message": None})
        return _attach_auth_cookies(response, result, remember_me=body.remember_me)
    except NotImplementedError:
        return _passkey_reserved()
    except Exception as exc:  # noqa: BLE001
        if "disabled" in str(exc).lower():
            return _passkey_reserved()
        return _err(exc, status=401)


@router.get("/auth/passkey")
def auth_passkey_list(authorization: str | None = Header(default=None)) -> JSONResponse:
    """List the authenticated user's registered passkeys (credential
    metadata only — public keys are never exposed)."""
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        return JSONResponse(
            {"ok": True, "result": _platform().webauthn_list_credentials(str(user["user_id"]))}
        )
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


@router.delete("/auth/passkey/{credential_id}")
def auth_passkey_delete(
    credential_id: str,
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    """Remove a passkey from the authenticated user's account."""
    try:
        token = _bearer(authorization)
        user = _platform().auth.current_user(token)
        meta = _client_meta(request)
        result = _platform().webauthn_remove_credential(
            str(user["user_id"]), credential_id, ip_hint=meta["ip_hint"]
        )
        return JSONResponse({"ok": True, "result": result})
    except Exception as exc:  # noqa: BLE001
        return _err(exc)


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
