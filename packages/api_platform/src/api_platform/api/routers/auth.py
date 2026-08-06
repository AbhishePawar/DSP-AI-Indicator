"""Auth routes — issue JWT / accept API keys (transport only). Additive PEP-001 fields.

EPIC-016: HttpOnly cookie session issuance when ``DSP_COOKIE_AUTH`` is enabled.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.exceptions import ApiError, ApiValidationError

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, max_length=256)
    remember_me: bool = False
    api_key_id: str | None = None
    api_key_secret: str | None = None


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = Field(default=None, min_length=16, max_length=512)


def _maybe_set_cookies(
    payload: dict,
    *,
    access_token: str,
    refresh_token: str | None = None,
    session_id: str | None = None,
    remember_me: bool = False,
    api_version: str = "v1",
    capability: str = "auth.login",
) -> JSONResponse:
    body = {
        "ok": True,
        "capability": capability,
        "payload": dict(payload),
        "api_version": api_version,
        "platform_version": None,
        "errors": [],
    }
    try:
        from security_platform.security.cookies import cookie_auth_enabled, set_auth_cookies

        if cookie_auth_enabled():
            response = JSONResponse(content=body)
            csrf = set_auth_cookies(
                response,
                access_token=access_token,
                refresh_token=refresh_token,
                session_id=session_id,
                remember_me=remember_me,
            )
            body["payload"]["csrf_token"] = csrf
            body["payload"]["cookie_auth"] = True
            response = JSONResponse(content=body)
            set_auth_cookies(
                response,
                access_token=access_token,
                refresh_token=refresh_token,
                session_id=session_id,
                remember_me=remember_me,
                csrf_token=csrf,
            )
            return response
    except Exception:  # noqa: BLE001
        pass
    return JSONResponse(content=body)


@router.post("/auth/login")
def login(body: LoginRequest, request: Request) -> JSONResponse:
    """Authenticate via username (+ optional password) or API key; return JWT.

    Passwordless username login remains for accounts without a password hash (RC
    compatibility). Accounts with a password hash require ``password``.
    Additive ``refresh_token`` may be returned when identity service is present.
    When cookie auth is enabled, HttpOnly cookies are also issued.
    """
    bundle = getattr(request.app.state, "security", None)
    if bundle is None:
        raise ApiError(
            "security bundle is not configured on the API",
            status_code=503,
        )

    if body.api_key_id and body.api_key_secret:
        principal = bundle.authentication.authenticate_api_key(
            body.api_key_id, body.api_key_secret
        )
        token = bundle.jwt.issue(
            subject=principal.subject,
            role=principal.role,
            username=principal.username,
        )
        return _maybe_set_cookies(
            {
                "access_token": token,
                "token_type": "bearer",
                "role": principal.role.value,
                "subject": principal.subject,
                "auth_method": "api_key",
            },
            access_token=token,
            remember_me=False,
            api_version=getattr(request.app.state.api, "api_version", "v1"),
        )

    username = (body.username or "").strip()
    if not username:
        raise ApiValidationError(
            "login requires username or api_key_id + api_key_secret"
        )

    identity = getattr(bundle, "identity", None)
    if identity is not None:
        try:
            pair = identity.authenticate(
                username,
                body.password,
                remember_me=body.remember_me,
            )
        except Exception as exc:
            status = 401
            if exc.__class__.__name__ == "RateLimitError":
                status = 429
            raise ApiError(str(exc) or "invalid credentials", status_code=status) from exc
        user = bundle.users.get_by_username(username)
        return _maybe_set_cookies(
            {
                "access_token": pair.access_token,
                "refresh_token": pair.refresh_token,
                "token_type": "bearer",
                "expires_in": pair.expires_in,
                "role": user.role.value,
                "subject": user.user_id,
                "username": user.username,
                "auth_method": "jwt",
                "session_id": pair.session_id,
            },
            access_token=pair.access_token,
            refresh_token=pair.refresh_token,
            session_id=pair.session_id,
            remember_me=body.remember_me,
            api_version=getattr(request.app.state.api, "api_version", "v1"),
        )

    # Legacy path without identity service
    try:
        user = bundle.users.get_by_username(username)
    except Exception as exc:
        raise ApiError("invalid credentials", status_code=401) from exc

    if not user.active:
        raise ApiError("user inactive", status_code=401)

    token = bundle.jwt.issue(
        subject=user.user_id,
        role=user.role,
        username=user.username,
    )
    return _maybe_set_cookies(
        {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role.value,
            "subject": user.user_id,
            "username": user.username,
            "auth_method": "jwt",
        },
        access_token=token,
        remember_me=body.remember_me,
        api_version=getattr(request.app.state.api, "api_version", "v1"),
    )


@router.post("/auth/refresh")
def refresh(body: RefreshRequest, request: Request) -> JSONResponse:
    """Rotate refresh token — additive PEP-001 endpoint. Cookie or body token."""
    bundle = getattr(request.app.state, "security", None)
    if bundle is None:
        raise ApiError(
            "security bundle is not configured on the API",
            status_code=503,
        )
    identity = getattr(bundle, "identity", None)
    if identity is None:
        raise ApiError("identity service is not configured", status_code=503)
    refresh_token = body.refresh_token
    if not refresh_token:
        try:
            from security_platform.security.cookies import read_refresh_token

            refresh_token = read_refresh_token(request)
        except Exception:  # noqa: BLE001
            refresh_token = None
    if not refresh_token:
        raise ApiValidationError("refresh_token required")
    try:
        pair = identity.refresh(refresh_token)
    except Exception as exc:
        raise ApiError(str(exc) or "invalid refresh token", status_code=401) from exc
    return _maybe_set_cookies(
        {
            "access_token": pair.access_token,
            "refresh_token": pair.refresh_token,
            "token_type": "bearer",
            "expires_in": pair.expires_in,
            "session_id": pair.session_id,
        },
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        session_id=pair.session_id,
        remember_me=False,
        api_version=getattr(request.app.state.api, "api_version", "v1"),
        capability="auth.refresh",
    )


@router.post("/auth/logout")
def logout(request: Request) -> JSONResponse:
    """Invalidate cookie session (EPIC-016)."""
    from security_platform.security.cookies import clear_auth_cookies, cookie_auth_enabled

    response = JSONResponse(
        content={
            "ok": True,
            "capability": "auth.logout",
            "payload": {"logged_out": True, "cookie_auth": cookie_auth_enabled()},
            "api_version": getattr(request.app.state.api, "api_version", "v1"),
        }
    )
    clear_auth_cookies(response)
    return response


@router.get("/auth/session")
def session_probe(request: Request) -> JSONResponse:
    """Return non-secret session metadata for cookie-mode SPA bootstrap."""
    from security_platform.security.cookies import (
        ACCESS_COOKIE,
        CSRF_COOKIE,
        SESSION_COOKIE,
        cookie_auth_enabled,
    )

    has_access = bool(request.cookies.get(ACCESS_COOKIE))
    return JSONResponse(
        content={
            "ok": True,
            "capability": "auth.session",
            "payload": {
                "cookie_auth": cookie_auth_enabled(),
                "authenticated": has_access,
                "session_id": request.cookies.get(SESSION_COOKIE),
                "csrf_token": request.cookies.get(CSRF_COOKIE),
            },
            "api_version": getattr(request.app.state.api, "api_version", "v1"),
        }
    )
