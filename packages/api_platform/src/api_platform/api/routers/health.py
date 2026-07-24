"""Health routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(state: ApiState = Depends(get_api_state)) -> HealthResponse:
    """Offline platform health check via ``DSPPlatform.health_check``."""
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
    meta = result.metadata
    return HealthResponse(
        status=status,
        ready=ready,
        api_version=state.api_version,
        platform_version=meta.version,
        checks=checks,
        limitations=list(result.limitations),
    )
