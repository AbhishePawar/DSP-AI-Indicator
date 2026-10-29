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
        from security_platform import cookie_auth_enabled, set_auth_cookies

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
            raise ApiError(
                str(exc) or "invalid credentials", status_code=status
            ) from exc
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
            from security_platform import read_refresh_token

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
    """Invalidate session and auth cookies (EPIC-016)."""
    from security_platform import (
        ACCESS_COOKIE,
        SESSION_COOKIE,
        clear_auth_cookies,
        cookie_auth_enabled,
        read_access_token,
        read_refresh_token,
    )

    cookie_access = request.cookies.get(ACCESS_COOKIE)
    auth_header = request.headers.get("authorization") or request.headers.get(
        "Authorization"
    )
    header_token = None
    if auth_header and auth_header.strip().lower().startswith("bearer "):
        header_token = auth_header.strip()[7:].strip() or None

    # Reject contradictory credentials between cookie and Authorization header
    if cookie_access and header_token and cookie_access != header_token:
        response = JSONResponse(
            status_code=400,
            content={
                "ok": False,
                "capability": "auth.logout",
                "error": "ConflictingCredentialsError",
                "message": "Conflicting credentials in cookie and Authorization header",
                "payload": {"logged_out": False, "cookie_auth": cookie_auth_enabled()},
                "api_version": getattr(request.app.state.api, "api_version", "v1"),
            },
        )
        clear_auth_cookies(response)
        return response

    access_token = read_access_token(request)
    refresh_token = read_refresh_token(request)
    cookie_session_id = request.cookies.get(SESSION_COOKIE)
    session_id: str | None = None

    # Derive validated session_id from authoritative credentials (never trust raw cookie alone)
    if access_token:
        try:
            from auth import get_auth_service

            auth_svc = get_auth_service()
            if auth_svc is not None:
                decoded = auth_svc.jwt.decode(access_token)
                sid = decoded.get("sid")
                if sid and cookie_session_id and cookie_session_id != sid:
                    response = JSONResponse(
                        status_code=400,
                        content={
                            "ok": False,
                            "capability": "auth.logout",
                            "error": "ConflictingCredentialsError",
                            "message": "Conflicting session credentials between cookie and token",
                            "payload": {
                                "logged_out": False,
                                "cookie_auth": cookie_auth_enabled(),
                            },
                            "api_version": getattr(
                                request.app.state.api, "api_version", "v1"
                            ),
                        },
                    )
                    clear_auth_cookies(response)
                    return response
                if sid:
                    session_id = sid
        except Exception:
            pass

    security = getattr(request.app.state, "security", None)
    if not session_id and access_token and security is not None:
        try:
            claims = security.jwt.verify(access_token)
            if hasattr(claims, "extra") and isinstance(claims.extra, dict):
                sid = claims.extra.get("sid")
                if sid and cookie_session_id and cookie_session_id != sid:
                    response = JSONResponse(
                        status_code=400,
                        content={
                            "ok": False,
                            "capability": "auth.logout",
                            "error": "ConflictingCredentialsError",
                            "message": "Conflicting session credentials between cookie and token",
                            "payload": {
                                "logged_out": False,
                                "cookie_auth": cookie_auth_enabled(),
                            },
                            "api_version": getattr(
                                request.app.state.api, "api_version", "v1"
                            ),
                        },
                    )
                    clear_auth_cookies(response)
                    return response
                if sid:
                    session_id = sid
        except Exception:
            pass

    if not session_id and refresh_token and security is not None:
        try:
            tokens_svc = getattr(getattr(security, "identity", None), "tokens", None)
            if tokens_svc is not None and hasattr(tokens_svc, "get_refresh_record"):
                rec = tokens_svc.get_refresh_record(refresh_token)
                if rec is not None and rec.session_id:
                    if cookie_session_id and cookie_session_id != rec.session_id:
                        response = JSONResponse(
                            status_code=400,
                            content={
                                "ok": False,
                                "capability": "auth.logout",
                                "error": "ConflictingCredentialsError",
                                "message": "Conflicting session credentials between cookie and refresh token",
                                "payload": {
                                    "logged_out": False,
                                    "cookie_auth": cookie_auth_enabled(),
                                },
                                "api_version": getattr(
                                    request.app.state.api, "api_version", "v1"
                                ),
                            },
                        )
                        clear_auth_cookies(response)
                        return response
                    session_id = rec.session_id
        except Exception:
            pass

    revocation_failed = False

    # 1. Authoritative AuthService session revocation for dsp-auth
    if session_id:
        try:
            from auth import get_auth_service

            auth_svc = get_auth_service()
            if auth_svc is not None and hasattr(auth_svc, "sessions"):
                sess = auth_svc.sessions.get(session_id)
                if sess is not None and not getattr(sess, "revoked", False):
                    api_state = getattr(request.app.state, "api", None)
                    platform = (
                        getattr(api_state, "platform", None)
                        if api_state is not None
                        else None
                    )
                    if platform is not None and hasattr(platform, "auth_logout"):
                        platform.auth_logout(session_id=session_id)
                    else:
                        auth_svc.logout(session_id=session_id)
        except Exception:
            revocation_failed = True

    # 2. Security Platform revocation for dsp-security
    if security is not None:
        identity = getattr(security, "identity", None)
        if identity is not None:
            try:
                identity.logout(
                    refresh_token=refresh_token,
                    session_id=session_id,
                )
            except Exception:
                revocation_failed = True

    if revocation_failed:
        response = JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "capability": "auth.logout",
                "error": "RevocationError",
                "message": "Failed to revoke session",
                "payload": {"logged_out": False, "cookie_auth": cookie_auth_enabled()},
                "api_version": getattr(request.app.state.api, "api_version", "v1"),
            },
        )
        clear_auth_cookies(response)
        return response

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
    from security_platform import (
        CSRF_COOKIE,
        SESSION_COOKIE,
        cookie_auth_enabled,
        read_access_token,
    )

    has_access = False
    session_id: str | None = None
    access_token = read_access_token(request)
    if access_token:
        # Prefer the authoritative platform auth boundary (used by /auth/rbac/me)
        api_state = getattr(request.app.state, "api", None)
        platform = (
            getattr(api_state, "platform", None) if api_state is not None else None
        )
        if platform is not None and hasattr(platform, "auth_current_user"):
            try:
                platform.auth_current_user(access_token)
                has_access = True
            except Exception:
                has_access = False
        else:
            try:
                from auth.enterprise_platform import get_enterprise_auth_platform

                get_enterprise_auth_platform().auth.current_user(access_token)
                has_access = True
            except Exception:
                has_access = False

        if has_access:
            session_id = request.cookies.get(SESSION_COOKIE)
            if not session_id:
                try:
                    from auth import get_auth_service

                    decoded = get_auth_service().jwt.decode(access_token)
                    session_id = decoded.get("sid")
                except Exception:
                    pass

        if not has_access:
            bundle = getattr(request.app.state, "security", None)
            if bundle is not None:
                try:
                    principal = bundle.authentication.authenticate_jwt(access_token)
                    has_access = True
                    session_id = (
                        request.cookies.get(SESSION_COOKIE) or principal.session_id
                    )
                except Exception:
                    has_access = False

    return JSONResponse(
        content={
            "ok": True,
            "capability": "auth.session",
            "payload": {
                "cookie_auth": cookie_auth_enabled(),
                "authenticated": has_access,
                "session_id": session_id if has_access else None,
                "csrf_token": request.cookies.get(CSRF_COOKIE),
            },
            "api_version": getattr(request.app.state.api, "api_version", "v1"),
        }
    )
