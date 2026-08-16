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


class RegisterRequest(BaseModel):
    """Email + password registration (email is the login identifier)."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)
    display_name: str | None = Field(default=None, max_length=128)


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=8, max_length=512)
    new_password: str = Field(min_length=1, max_length=256)


class VerifyEmailConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=8, max_length=512)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=254)


def _principal_from_request(request: Request, bundle):
    """Resolve the authenticated principal from a cookie or Bearer token."""
    token = None
    try:
        from security_platform import ACCESS_COOKIE

        token = request.cookies.get(ACCESS_COOKIE)
    except Exception:  # noqa: BLE001
        token = None
    if not token:
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            token = header[7:].strip()
    if not token:
        raise ApiError("not authenticated", status_code=401)
    try:
        return bundle.authentication.authenticate_jwt(token)
    except Exception as exc:  # noqa: BLE001
        raise ApiError("invalid or expired token", status_code=401) from exc


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
    """Invalidate cookie session (EPIC-016)."""
    from security_platform import clear_auth_cookies, cookie_auth_enabled

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


@router.post("/auth/register")
def register(body: RegisterRequest, request: Request) -> JSONResponse:
    """Register a new account with email + password, then issue a JWT session.

    Email is the login identifier (stored as the username). Extends the existing
    ``security_platform`` IdentityService (Argon2/scrypt hashing + policy).
    """
    bundle = getattr(request.app.state, "security", None)
    if bundle is None:
        raise ApiError("security bundle is not configured on the API", status_code=503)
    identity = getattr(bundle, "identity", None)
    if identity is None:
        raise ApiError("identity service is not configured", status_code=503)

    email = (body.email or "").strip().lower()
    if "@" not in email:
        raise ApiValidationError("a valid email address is required")

    try:
        bundle.users.get_by_username(email)
        raise ApiError("email already registered", status_code=409)
    except ApiError:
        raise
    except Exception:  # noqa: BLE001 — SecurityError means "not found" => proceed
        pass

    try:
        identity.provision(
            username=email,
            role="CLIENT",
            password=body.password,
            email=email,
            display_name=body.display_name or email.split("@")[0],
        )
    except Exception as exc:  # noqa: BLE001 — password policy / duplicate
        raise ApiValidationError(str(exc) or "registration failed") from exc

    try:
        pair = identity.authenticate(email, body.password)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(str(exc) or "authentication failed", status_code=401) from exc
    user = bundle.users.get_by_username(email)
    return _maybe_set_cookies(
        {
            "access_token": pair.access_token,
            "refresh_token": pair.refresh_token,
            "token_type": "bearer",
            "expires_in": pair.expires_in,
            "role": user.role.value,
            "subject": user.user_id,
            "username": user.username,
            "email": user.email,
            "auth_method": "jwt",
            "session_id": pair.session_id,
        },
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        session_id=pair.session_id,
        api_version=getattr(request.app.state.api, "api_version", "v1"),
        capability="auth.register",
    )


@router.get("/auth/me")
def me(request: Request) -> JSONResponse:
    """Return the authenticated user's profile (cookie or Bearer token)."""
    bundle = getattr(request.app.state, "security", None)
    if bundle is None:
        raise ApiError("security bundle is not configured on the API", status_code=503)

    token = None
    try:
        from security_platform import ACCESS_COOKIE

        token = request.cookies.get(ACCESS_COOKIE)
    except Exception:  # noqa: BLE001
        token = None
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
    if not token:
        raise ApiError("not authenticated", status_code=401)

    try:
        principal = bundle.authentication.authenticate_jwt(token)
    except Exception as exc:  # noqa: BLE001
        raise ApiError("invalid or expired token", status_code=401) from exc

    email = None
    try:
        user = bundle.users.get_by_username(principal.username or "")
        email = user.email
    except Exception:  # noqa: BLE001
        user = None
    return JSONResponse(
        content={
            "ok": True,
            "capability": "auth.me",
            "payload": {
                "subject": principal.subject,
                "username": principal.username,
                "email": email,
                "role": principal.role.value,
                "authenticated": True,
            },
            "api_version": getattr(request.app.state.api, "api_version", "v1"),
            "errors": [],
        }
    )


@router.post("/auth/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request) -> JSONResponse:
    """Request a password-reset token. Never reveals whether the email exists."""
    bundle = getattr(request.app.state, "security", None)
    identity = getattr(bundle, "identity", None) if bundle else None
    if identity is None:
        raise ApiError("identity service is not configured", status_code=503)
    email = (body.email or "").strip().lower()
    token = identity.request_password_reset(email) if email else None
    import os as _os

    is_prod = _os.environ.get("DSP_ENVIRONMENT", "development").lower() == "production"
    payload = {"requested": True, "email": email or None}
    # No email provider wired: expose the token only outside production so the
    # flow is testable. In production the token must be delivered out-of-band.
    if token and not is_prod:
        payload["reset_token"] = token
    return JSONResponse(
        content={"ok": True, "capability": "auth.forgot_password", "payload": payload,
                 "api_version": getattr(request.app.state.api, "api_version", "v1"), "errors": []}
    )


@router.post("/auth/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request) -> JSONResponse:
    """Complete a password reset using the opaque token."""
    bundle = getattr(request.app.state, "security", None)
    identity = getattr(bundle, "identity", None) if bundle else None
    if identity is None:
        raise ApiError("identity service is not configured", status_code=503)
    try:
        user = identity.confirm_password_reset(body.token, body.new_password)
    except Exception as exc:  # noqa: BLE001 — invalid/expired token or policy
        raise ApiError(str(exc) or "password reset failed", status_code=400) from exc
    return JSONResponse(
        content={"ok": True, "capability": "auth.reset_password",
                 "payload": {"reset": True, "username": user.username},
                 "api_version": getattr(request.app.state.api, "api_version", "v1"), "errors": []}
    )


@router.post("/auth/verify-email/request")
def request_email_verification(request: Request) -> JSONResponse:
    """Issue an email-verification token for the authenticated user."""
    bundle = getattr(request.app.state, "security", None)
    identity = getattr(bundle, "identity", None) if bundle else None
    if identity is None:
        raise ApiError("identity service is not configured", status_code=503)
    principal = _principal_from_request(request, bundle)
    token = identity.issue_email_verification(principal.subject)
    import os as _os

    is_prod = _os.environ.get("DSP_ENVIRONMENT", "development").lower() == "production"
    payload = {"requested": True}
    if not is_prod:
        payload["verification_token"] = token
    return JSONResponse(
        content={"ok": True, "capability": "auth.verify_email_request", "payload": payload,
                 "api_version": getattr(request.app.state.api, "api_version", "v1"), "errors": []}
    )


@router.post("/auth/verify-email/confirm")
def confirm_email_verification(body: VerifyEmailConfirmRequest, request: Request) -> JSONResponse:
    """Confirm an email-verification token."""
    bundle = getattr(request.app.state, "security", None)
    identity = getattr(bundle, "identity", None) if bundle else None
    if identity is None:
        raise ApiError("identity service is not configured", status_code=503)
    try:
        user = identity.confirm_email_verification(body.token)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(str(exc) or "verification failed", status_code=400) from exc
    return JSONResponse(
        content={"ok": True, "capability": "auth.verify_email_confirm",
                 "payload": {"email_verified": True, "username": user.username},
                 "api_version": getattr(request.app.state.api, "api_version", "v1"), "errors": []}
    )


@router.get("/auth/session")
def session_probe(request: Request) -> JSONResponse:
    """Return non-secret session metadata for cookie-mode SPA bootstrap."""
    from security_platform import (
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
