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

__all__ = [
    "SecurityMiddleware",
    "PATH_PERMISSIONS",
]

PATH_PERMISSIONS: dict[str, Permission] = {
    "/analyze/company": Permission.ANALYZE_COMPANY,
    "/api/v1/analyze/company": Permission.ANALYZE_COMPANY,
    "/compare": Permission.COMPARE_COMPANIES,
    "/api/v1/compare": Permission.COMPARE_COMPANIES,
    "/workflow/run": Permission.RUN_WORKFLOW,
    "/api/v1/workflow/run": Permission.RUN_WORKFLOW,
    "/copilot/chat": Permission.ASK_COPILOT,
    "/api/v1/copilot/chat": Permission.ASK_COPILOT,
}


def _permission_for_path(path: str) -> Permission | None:
    if path in PATH_PERMISSIONS:
        return PATH_PERMISSIONS[path]
    if path.startswith("/report/") or path.startswith("/api/v1/report/"):
        return Permission.VIEW_REPORTS
    return None


class SecurityMiddleware(BaseHTTPMiddleware):
    """Authenticate / authorize HTTP requests; attach ``request.state.security``.

    Does not import or call ``dsp_platform``. Public paths skip auth when
    configured. Guest mode is optional via ``SecuritySettings.allow_guest``.
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

        if path in settings.public_paths or not settings.require_auth:
            # Still attach guest/anonymous context when possible.
            try:
                if settings.allow_guest:
                    principal = self._bundle.authentication.guest_principal()
                else:
                    principal = self._bundle.authentication.authenticate_headers(
                        authorization=request.headers.get("authorization"),
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
            principal = self._bundle.authentication.authenticate_headers(
                authorization=request.headers.get("authorization"),
                api_key_id=request.headers.get("x-api-key-id"),
                api_key_secret=request.headers.get("x-api-key-secret"),
            )
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
