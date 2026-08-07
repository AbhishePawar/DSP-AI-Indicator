"""RC1 Milestone 10 — thin Production Operations routes under /ops/*.

Delegates to DSPPlatform.run_production_ops. Reuses existing /health and
/metrics — does not duplicate scrape or probe engines.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.ops import metrics_registry

router = APIRouter(tags=["ops"])


class OpsPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    backup_action: str | None = Field(None, max_length=32)
    snapshot_id: str | None = Field(None, max_length=128)
    label: str | None = Field(None, max_length=128)
    limit: int | None = Field(None, ge=1, le=100)


def _dispatch(
    state: ApiState,
    action: str,
    payload: dict[str, Any] | None = None,
) -> JSONResponse:
    try:
        result = state.platform.run_production_ops(
            action, api_state=state, payload=payload
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": str(exc), "message": "Data unavailable."},
        )
    status = 200 if result.get("ok") is not False else 400
    # Readiness-style 503 when ready probe fails
    if action == "ready" and isinstance(result.get("result"), dict):
        if result["result"].get("ready") is False:
            status = 503
    return JSONResponse(status_code=status, content=result)


@router.get("/ops/schema")
def ops_schema(state: ApiState = Depends(get_api_state)) -> dict[str, Any]:
    return {"ok": True, "schema": state.platform.production_ops_schema()}


@router.get("/ops/health")
def ops_health(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "health")


@router.get("/ops/health/live")
def ops_live(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "live")


@router.get("/ops/health/ready")
def ops_ready(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "ready")


@router.get("/ops/health/startup")
def ops_startup(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "startup")


@router.get("/ops/status")
def ops_status(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "status")


@router.get("/ops/version")
def ops_version(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "version")


@router.get("/ops/dependencies")
def ops_dependencies(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "dependencies")


@router.get("/ops/metrics")
def ops_metrics(
    format: str = Query("summary", pattern="^(summary|prometheus)$"),
    state: ApiState = Depends(get_api_state),
) -> Any:
    """Prometheus text when format=prometheus; otherwise JSON summary (no duplicate scrape)."""
    if format == "prometheus":
        return PlainTextResponse(
            metrics_registry.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )
    return _dispatch(state, "metrics")


@router.get("/ops/observability")
def ops_observability(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "observability")


@router.get("/ops/backup")
def ops_backup_status(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "backup", {"backup_action": "status"})


@router.post("/ops/backup")
def ops_backup_action(
    body: OpsPayload,
    state: ApiState = Depends(get_api_state),
) -> JSONResponse:
    return _dispatch(state, "backup", body.model_dump(exclude_none=True))


@router.get("/ops/secrets")
def ops_secrets(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "secrets")


@router.get("/ops/dashboard")
def ops_dashboard(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    return _dispatch(state, "dashboard")
