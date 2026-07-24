"""Auth routes — issue JWT / accept API keys (transport only)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.exceptions import ApiError, ApiValidationError
from api_platform.api.schemas import ApiResponse

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, max_length=128)
    api_key_id: str | None = None
    api_key_secret: str | None = None


@router.post("/auth/login", response_model=ApiResponse)
def login(body: LoginRequest, request: Request) -> ApiResponse:
    """Authenticate via username (seeded user) or API key; return JWT.

    No password store in RC — username must match a registered UserStore
    entry. Not a business endpoint.
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
