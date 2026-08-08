"""FastAPI dependency injection — platform + ephemeral registries (K1.1)."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable

from fastapi import HTTPException, Request

from api_platform.api.exceptions import ApiNotFoundError
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration

try:
    from llm_adapters import CopilotCompleteService, build_default_registry
except ImportError:  # pragma: no cover - optional during partial installs
    CopilotCompleteService = None  # type: ignore[misc, assignment]
    build_default_registry = None  # type: ignore[misc, assignment]

__all__ = [
    "ApiState",
    "ReportStore",
    "ContextStore",
    "get_api_state",
    "get_platform",
    "get_report_store",
    "get_context_store",
    "build_default_platform",
    "resolve_access_token",
    "require_authenticated_actor",
    "require_admin_access",
]


@dataclass
class ReportStore:
    """Process-local ephemeral report registry — not durable persistence."""

    _items: dict[str, Any] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def put(self, report_id: str, payload: Any) -> str:
        key = report_id.strip()
        if not key:
            msg = "report_id must not be empty"
            raise ValueError(msg)
        with self._lock:
            self._items[key] = payload
        return key

    def get(self, report_id: str) -> Any:
        key = report_id.strip()
        with self._lock:
            if key not in self._items:
                msg = f"report not found: {report_id!r}"
                raise ApiNotFoundError(msg)
            return self._items[key]

    def has(self, report_id: str) -> bool:
        with self._lock:
            return report_id.strip() in self._items


@dataclass
class ContextStore:
    """Process-local opaque context handles for workflow / copilot routes."""

    _items: dict[str, Any] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)

    def put(self, context_id: str, payload: Any) -> str:
        key = context_id.strip()
        if not key:
            msg = "context_id must not be empty"
            raise ValueError(msg)
        with self._lock:
            self._items[key] = payload
        return key

    def get(self, context_id: str) -> Any:
        key = context_id.strip()
        with self._lock:
            if key not in self._items:
                msg = f"context not found: {context_id!r}"
                raise ApiNotFoundError(msg)
            return self._items[key]


@dataclass
class ApiState:
    """Application-scoped API dependencies."""

    platform: DSPPlatform
    reports: ReportStore = field(default_factory=ReportStore)
    contexts: ContextStore = field(default_factory=ContextStore)
    api_version: str = "v1"
    copilot_service: Any = field(default=None)
    language_model: Any | None = None
    # EPIC-011A — optional production infra (duck-typed)
    infrastructure: Any | None = None
    production: Any | None = None
    infra_notes: tuple[str, ...] = ()


def build_copilot_service() -> Any:
    if CopilotCompleteService is None:
        return None
    return CopilotCompleteService(build_default_registry())


def build_language_model(registry: Any | None = None) -> Any | None:
    if build_default_registry is None:
        return None
    reg = registry or build_default_registry()
    _, adapter = reg.resolve_active()
    return adapter


def build_default_platform() -> DSPPlatform:
    """Build a ready platform shell for API hosting.

    Uses ``require_analysis_service=False`` so the HTTP app can start without
    live provider secrets. Analyze routes still require a wired analysis
    service (injected via ``PlatformBuilder`` / app lifespan override).
    """
    return (
        PlatformBuilder()
        .with_configuration(
            PlatformConfiguration(require_analysis_service=False)
        )
        .auto_ready(True)
        .build()
    )


def get_api_state(request: Request) -> ApiState:
    """Resolve ``ApiState`` from the FastAPI application."""
    state = getattr(request.app.state, "api", None)
    if state is None:
        msg = "API state is not configured on the application"
        raise RuntimeError(msg)
    return state


def get_platform(request: Request) -> DSPPlatform:
    """Dependency: DSPPlatform instance."""
    return get_api_state(request).platform


def get_report_store(request: Request) -> ReportStore:
    """Dependency: ephemeral report store."""
    return get_api_state(request).reports


def get_context_store(request: Request) -> ContextStore:
    """Dependency: ephemeral context store."""
    return get_api_state(request).contexts


PlatformFactory = Callable[[], DSPPlatform]


def resolve_access_token(request: Request) -> str | None:
    """Extract Bearer or HttpOnly access cookie — never client identity headers."""
    auth_header = request.headers.get("authorization") or ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if token:
            return token
    try:
        from security_platform import read_access_token

        cookie_token = read_access_token(request)
        if cookie_token:
            return str(cookie_token).strip() or None
    except Exception:  # noqa: BLE001
        return None
    return None


def require_authenticated_actor(request: Request) -> dict[str, Any]:
    """P0-05 — resolve actor solely from server-validated JWT/session.

    Client headers such as ``X-User-Id`` and body ``actor_user_id`` are never
    authoritative identity.
    """
    token = resolve_access_token(request)
    if not token:
        raise HTTPException(
            status_code=401,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        from auth import get_auth_service

        auth = get_auth_service()
        user = auth.current_user(token)
        uid = str(user.get("user_id") or "").strip()
        if not uid:
            raise HTTPException(
                status_code=401,
                detail="authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"user_id": uid, "user": user}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=401,
            detail="authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_admin_access(request: Request) -> dict[str, Any]:
    """P0-05 — always gate admin / control-center / sensitive ops routes.

    Requires Bearer/cookie access token with ``configure_platform`` or
    ``manage_users`` via the institutional auth package.
    """
    actor = require_authenticated_actor(request)
    user = actor.get("user") or {}
    uid = str(actor.get("user_id") or "")

    try:
        from auth import get_auth_service

        auth = get_auth_service()
        allowed = False
        for perm in ("configure_platform", "manage_users"):
            try:
                auth.require_permission(user, perm)
                allowed = True
                break
            except Exception:  # noqa: BLE001
                continue
        if not allowed:
            raise HTTPException(status_code=403, detail="admin permission required")
        return {"user_id": uid, "user": user}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=401,
            detail="admin authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
