"""Health routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.ops import collect_health_snapshot, get_build_metadata
from api_platform.api.schemas import HealthResponse
from dsp_platform import COMPOSITION_PIPELINE_VERSION

router = APIRouter(tags=["health"])


def _platform_health(state: ApiState) -> tuple[bool, str, list[dict[str, Any]]]:
    result = state.platform.health_check()
    payload = result.payload
    checks: list[dict[str, Any]] = []
    ready = bool(result.ok)
    status = "pass" if ready else "fail"
    if payload is not None:
        ready = bool(getattr(payload, "ready", ready))
        status_obj = getattr(payload, "status", None)
        if status_obj is not None:
            status = getattr(status_obj, "value", str(status_obj))
        for check in getattr(payload, "checks", ()) or ():
            checks.append(
                {
                    "name": getattr(check, "name", "unknown"),
                    "status": getattr(
                        getattr(check, "status", None), "value", "unknown"
                    ),
                    "message": getattr(check, "message", ""),
                }
            )
    checks.append(
        {
            "name": "composition_pipeline",
            "status": "pass",
            "message": f"pipeline={COMPOSITION_PIPELINE_VERSION}",
        }
    )
    return ready, status, checks


@router.get("/health", response_model=HealthResponse)
def health(state: ApiState = Depends(get_api_state)) -> HealthResponse:
    """Offline platform health check via ``DSPPlatform.health_check``."""
    ready, status, checks = _platform_health(state)
    result = state.platform.health_check()
    meta = result.metadata
    return HealthResponse(
        status=status,
        ready=ready,
        api_version=state.api_version,
        platform_version=meta.version,
        pipeline_version=COMPOSITION_PIPELINE_VERSION,
        repository_version=meta.version,
        checks=checks,
        limitations=list(result.limitations),
    )


@router.get("/health/live")
def health_live() -> JSONResponse:
    """Liveness probe — process is running."""
    build = get_build_metadata()
    return JSONResponse(
        {
            "status": "alive",
            "application_version": build.application_version,
            "release_channel": build.release_channel,
        }
    )


@router.get("/health/ready")
def health_ready(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    """Readiness probe — platform and ops dependencies available."""
    platform_ready, status, checks = _platform_health(state)
    snapshot = collect_health_snapshot(state)
    ops_ready = bool(snapshot.get("service_readiness", {}).get("copilot_service"))
    ready = ops_ready
    snapshot["status"] = "pass" if ready else status
    snapshot["ready"] = ready
    snapshot["platform_ready"] = platform_ready
    snapshot["checks"] = checks
    code = 200 if ready else 503
    return JSONResponse(snapshot, status_code=code)
