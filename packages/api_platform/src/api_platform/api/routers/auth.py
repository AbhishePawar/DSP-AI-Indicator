"""Auth routes — issue JWT / accept API keys (transport only). Additive PEP-001 fields."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.exceptions import ApiError, ApiValidationError
from api_platform.api.schemas import ApiResponse

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

    refresh_token: str = Field(min_length=16, max_length=512)


@router.post("/auth/login", response_model=ApiResponse)
def login(body: LoginRequest, request: Request) -> ApiResponse:
    """Authenticate via username (+ optional password) or API key; return JWT.

    Passwordless username login remains for accounts without a password hash (RC
    compatibility). Accounts with a password hash require ``password``.
    Additive ``refresh_token`` may be returned when identity service is present.
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
        return ApiResponse(
            ok=True,
            capability="auth.login",
            payload={
                "access_token": token,
                "token_type": "bearer",
                "role": principal.role.value,
                "subject": principal.subject,
                "auth_method": "api_key",
            },
            api_version=getattr(request.app.state.api, "api_version", "v1"),
            platform_version=None,
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
        return ApiResponse(
            ok=True,
            capability="auth.login",
            payload={
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
            api_version=getattr(request.app.state.api, "api_version", "v1"),
            platform_version=None,
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
    return ApiResponse(
        ok=True,
        capability="auth.login",
        payload={
            "access_token": token,
            "token_type": "bearer",
            "role": user.role.value,
            "subject": user.user_id,
            "username": user.username,
            "auth_method": "jwt",
        },
        api_version=getattr(request.app.state.api, "api_version", "v1"),
        platform_version=None,
    )


@router.post("/auth/refresh", response_model=ApiResponse)
def refresh(body: RefreshRequest, request: Request) -> ApiResponse:
    """Rotate refresh token — additive PEP-001 endpoint."""
    bundle = getattr(request.app.state, "security", None)
    if bundle is None:
        raise ApiError(
            "security bundle is not configured on the API",
            status_code=503,
        )
    identity = getattr(bundle, "identity", None)
    if identity is None:
        raise ApiError("identity service is not configured", status_code=503)
    try:
        pair = identity.refresh(body.refresh_token)
    except Exception as exc:
        raise ApiError(str(exc) or "invalid refresh token", status_code=401) from exc
    return ApiResponse(
        ok=True,
        capability="auth.refresh",
        payload={
            "access_token": pair.access_token,
            "refresh_token": pair.refresh_token,
            "token_type": "bearer",
            "expires_in": pair.expires_in,
            "session_id": pair.session_id,
        },
        api_version=getattr(request.app.state.api, "api_version", "v1"),
        platform_version=None,
    )
