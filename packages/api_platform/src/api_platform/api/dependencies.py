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
    "DatabaseReportStore",
    "ContextStore",
    "get_api_state",
    "get_platform",
    "get_report_store",
    "get_context_store",
    "build_default_platform",
    "resolve_access_token",
    "require_authenticated_actor",
    "require_admin_access",
    "build_report_store",
]


@dataclass
class ReportStore:
    """Report registry — process-local unless replaced by DatabaseReportStore."""

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


class DatabaseReportStore(ReportStore):
    """P0-06 — report registry shared via DatabasePort snapshots."""

    _TABLE = "api_report_snapshots"
    _KEY = "reports_v1"

    def __init__(self, database: Any) -> None:
        super().__init__()
        self._db = database
        self._persist_lock = Lock()
        self._ensure_schema()
        self._hydrate()

    def _ensure_schema(self) -> None:
        self._db.execute(
            f"CREATE TABLE IF NOT EXISTS {self._TABLE} ("
            "snapshot_key TEXT PRIMARY KEY, "
            "payload TEXT NOT NULL, "
            "updated_at TEXT NOT NULL"
            ")"
        )

    def _hydrate(self) -> None:
        import base64
        import json

        rows = self._db.fetchall(f"SELECT * FROM {self._TABLE}")
        payload: dict[str, Any] | None = None
        for row in rows:
            if str(row.get("snapshot_key")) != self._KEY:
                continue
            raw = row.get("payload")
            if isinstance(raw, dict):
                payload = raw
            elif isinstance(raw, str) and raw:
                try:
                    decoded = base64.b64decode(raw.encode("ascii")).decode("utf-8")
                    data = json.loads(decoded)
                    payload = data if isinstance(data, dict) else None
                except Exception:  # noqa: BLE001
                    payload = None
            break
        with self._lock:
            self._items = dict((payload or {}).get("items") or {})

    def _flush(self) -> None:
        import base64
        import json
        from datetime import UTC, datetime

        with self._persist_lock:
            with self._lock:
                items = dict(self._items)
            encoded = base64.b64encode(
                json.dumps({"items": items}, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            now = datetime.now(tz=UTC).isoformat().replace("'", "''")
            key = self._KEY.replace("'", "''")
            enc = encoded.replace("'", "''")
            self._db.execute(f"DELETE FROM {self._TABLE}")
            self._db.execute(
                f"INSERT INTO {self._TABLE} (snapshot_key, payload, updated_at) "
                f"VALUES ('{key}', '{enc}', '{now}')"
            )

    def put(self, report_id: str, payload: Any) -> str:
        self._hydrate()
        key = super().put(report_id, payload)
        self._flush()
        return key

    def get(self, report_id: str) -> Any:
        self._hydrate()
        return super().get(report_id)

    def has(self, report_id: str) -> bool:
        self._hydrate()
        return super().has(report_id)


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


def build_report_store(database: Any | None = None) -> ReportStore:
    """P0-06 — durable reports when DatabasePort is available."""
    if database is None:
        return ReportStore()
    return DatabaseReportStore(database)


def get_report_store(request: Request) -> ReportStore:
    """Dependency: report store (durable when wired at app boot)."""
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
