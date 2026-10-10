"""ASGI / Starlette security middleware."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from security_platform.security.auth import SecurityBundle
from security_platform.security.exceptions import (
    AuthenticationError,
    AuthorizationError,
    RateLimitError,
    SecurityError,
)
from security_platform.security.permissions import Permission
from security_platform.security.roles import ROLE_PERMISSIONS, Role
from security_platform.security.users import UserPrincipal

__all__ = [
    "SecurityMiddleware",
    "PATH_PERMISSIONS",
]

PATH_PERMISSIONS: dict[str, Permission] = {
    "/analyze/company": Permission.ANALYZE_COMPANY,
    "/api/v1/analyze/company": Permission.ANALYZE_COMPANY,
    "/analyse": Permission.ANALYZE_COMPANY,
    "/api/v1/analyse": Permission.ANALYZE_COMPANY,
    "/validate": Permission.ANALYZE_COMPANY,
    "/api/v1/validate": Permission.ANALYZE_COMPANY,
    "/compare": Permission.COMPARE_COMPANIES,
    "/api/v1/compare": Permission.COMPARE_COMPANIES,
    "/workflow/run": Permission.RUN_WORKFLOW,
    "/api/v1/workflow/run": Permission.RUN_WORKFLOW,
    "/copilot/chat": Permission.ASK_COPILOT,
    "/api/v1/copilot/chat": Permission.ASK_COPILOT,
    "/copilot/complete": Permission.ASK_COPILOT,
    "/api/v1/copilot/complete": Permission.ASK_COPILOT,
    "/copilot/stream": Permission.ASK_COPILOT,
    "/api/v1/copilot/stream": Permission.ASK_COPILOT,
    "/research/export": Permission.VIEW_REPORTS,
    "/api/v1/research/export": Permission.VIEW_REPORTS,
    "/research/report": Permission.VIEW_REPORTS,
    "/api/v1/research/report": Permission.VIEW_REPORTS,
    "/research/company": Permission.ANALYZE_COMPANY,
    "/api/v1/research/company": Permission.ANALYZE_COMPANY,
}


def _permission_for_path(path: str) -> Permission | None:
    if path in PATH_PERMISSIONS:
        return PATH_PERMISSIONS[path]
    if path.startswith("/report/") or path.startswith("/api/v1/report/"):
        return Permission.VIEW_REPORTS
    return None


def _is_institutional_auth_zone(path: str) -> bool:
    """Institutional RBAC/admin uses the ``auth`` package JWT — not security_platform."""
    return (
        path.startswith("/admin")
        or path.startswith("/api/v1/admin")
        or path.startswith("/auth/rbac")
        or path.startswith("/api/v1/auth/rbac")
        or path.startswith("/auth/enterprise")
        or path.startswith("/api/v1/auth/enterprise")
        or path.startswith("/enterprise")
        or path.startswith("/api/v1/enterprise")
        or path.startswith("/beta")
        or path.startswith("/api/v1/beta")
    )


class SecurityMiddleware(BaseHTTPMiddleware):
    """Authenticate / authorize HTTP requests; attach ``request.state.security``.

    Does not import or call ``dsp_platform``. Public paths skip auth when
    configured. Guest mode is optional via ``SecuritySettings.allow_guest``.
    Institutional ``/admin`` and ``/auth/rbac`` zones are delegated to the
    EPIC-A009/A010 stack (see ``require_admin_access``).
    """

    def __init__(self, app: Any, *, bundle: SecurityBundle) -> None:
        super().__init__(app)
        self._bundle = bundle

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        path = request.url.path
        settings = self._bundle.settings

        auth_header = _authorization_from_request(request)

        if (
            path in settings.public_paths
            or not settings.require_auth
            or _is_institutional_auth_zone(path)
        ):
            # Still attach guest/anonymous context when possible.
            try:
                if settings.allow_guest:
                    principal = self._bundle.authentication.guest_principal()
                else:
                    principal = self._bundle.authentication.authenticate_headers(
                        authorization=auth_header,
                        api_key_id=request.headers.get("x-api-key-id"),
                        api_key_secret=request.headers.get("x-api-key-secret"),
                    )
            except AuthenticationError:
                principal = None
            if principal is not None:
                request.state.security = self._bundle.authentication.build_context(
                    principal,
                    request_id=getattr(request.state, "request_id", None),
                )
            return await call_next(request)

        try:
            try:
                principal = self._bundle.authentication.authenticate_headers(
                    authorization=auth_header,
                    api_key_id=request.headers.get("x-api-key-id"),
                    api_key_secret=request.headers.get("x-api-key-secret"),
                )
            except AuthenticationError:
                # The public login UI uses the enterprise AuthService. Accept
                # its signed bearer token here as well, then apply this
                # middleware's normal role-to-permission checks. Do not accept
                # a token unless the canonical AuthService validates it.
                principal = _authenticate_enterprise_bearer(auth_header)
                if principal is None:
                    raise
            self._bundle.rate_limiter.check(principal.subject)
            permission = _permission_for_path(path)
            if permission is not None:
                self._bundle.authorization.check(principal, permission)
            context = self._bundle.authentication.build_context(
                principal,
                request_id=getattr(request.state, "request_id", None),
            )
            request.state.security = context
            self._bundle.audit.log(
                action="authorize",
                subject=principal.subject,
                success=True,
                permission=permission.value if permission else None,
                path=path,
                request_id=context.request_id,
            )
        except AuthenticationError as exc:
            self._bundle.audit.log(
                action="authenticate",
                subject="anonymous",
                success=False,
                detail=str(exc),
                path=path,
            )
            return _error_response(401, "AuthenticationError", str(exc))
        except AuthorizationError as exc:
            self._bundle.audit.log(
                action="authorize",
                subject=principal.subject,
                success=False,
                detail=str(exc),
                path=path,
            )
            return _error_response(403, "AuthorizationError", str(exc))
        except RateLimitError as exc:
            return _error_response(429, "RateLimitError", str(exc))
        except SecurityError as exc:
            return _error_response(400, "SecurityError", str(exc))

        return await call_next(request)




def _authenticate_enterprise_bearer(authorization: str | None) -> UserPrincipal | None:
    """Validate an enterprise AuthService bearer token for the API gateway.

    Login and user persistence are owned by the auth package; the standalone
    SecurityBundle JWT is a separate offline/CI identity system. This bridge
    validates through the canonical AuthService and maps roles conservatively
    into the gateway's frozen permission model. Unknown roles fail closed.
    """
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.strip().lower() != "bearer" or not token.strip():
        return None
    try:
        from auth import get_auth_service

        user = get_auth_service().current_user(token.strip())
        roles = {str(role).strip().lower() for role in (user.get("roles") or [])}
        if roles.intersection({"super_admin", "administrator", "admin"}):
            role = Role.ADMIN
        elif roles.intersection({"advisor", "analyst"}):
            role = Role.ADVISOR
        elif "researcher" in roles:
            role = Role.RESEARCHER
        elif "api" in roles:
            role = Role.API
        elif roles.intersection({"client", "enterprise_client", "read_only", "viewer"}):
            role = Role.CLIENT
        else:
            return None
        subject = str(user.get("user_id") or "").strip()
        username = str(user.get("username") or "").strip()
        if not subject or not username:
            return None
        return UserPrincipal(
            subject=subject,
            role=role,
            permissions=ROLE_PERMISSIONS[role],
            auth_method="enterprise_jwt",
            username=username,
        )
    except Exception:  # noqa: BLE001 — invalid or unavailable identity fails closed
        return None


def _authorization_from_request(request: Request) -> str | None:
    """Prefer Authorization header; fall back to HttpOnly access cookie (EPIC-016)."""
    header = request.headers.get("authorization")
    if header:
        return header
    try:
        from security_platform.security.cookies import (
            ACCESS_COOKIE,
            cookie_auth_enabled,
        )

        if cookie_auth_enabled():
            token = request.cookies.get(ACCESS_COOKIE)
            if token:
                return f"Bearer {token}"
    except Exception:  # noqa: BLE001 — never break auth stack on cookie helper issues
        pass
    return None


def _error_response(status: int, error: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "ok": False,
            "error": error,
            "detail": detail,
            "api_version": "v1",
            "status_code": status,
        },
    )
