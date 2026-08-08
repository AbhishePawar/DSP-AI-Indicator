"""Health routes (EPIC-011A dependency probes)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api_platform.api.dependencies import ApiState, get_api_state
from api_platform.api.monitoring import (
    PlatformLifecycleState,
    get_lifecycle_state,
)
from api_platform.api.ops import (
    collect_component_statuses,
    collect_health_snapshot,
    get_build_metadata,
    resolve_platform_status,
)
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


def _append_infra_checks(state: ApiState, checks: list[dict[str, Any]]) -> None:
    """Append DB/Redis dependency checks from InfrastructureBundle when present."""
    infra = getattr(state, "infrastructure", None)
    if infra is None or not hasattr(infra, "health_checks"):
        return
    try:
        probes = infra.health_checks()
    except Exception:  # noqa: BLE001
        checks.append(
            {
                "name": "infrastructure",
                "status": "fail",
                "message": "dependency probe failed",
            }
        )
        return
    checks.append(
        {
            "name": "database",
            "status": "pass" if probes.get("database") else "fail",
            "message": f"adapter={probes.get('database_adapter', 'unknown')}",
        }
    )
    redis = probes.get("redis") or {}
    checks.append(
        {
            "name": "redis",
            "status": str(redis.get("status", "skip")),
            "message": (
                f"cache={probes.get('cache_adapter')} "
                f"fallback={redis.get('fallback_active')}"
            ),
        }
    )


@router.get("/health", response_model=HealthResponse)
def health(state: ApiState = Depends(get_api_state)) -> HealthResponse:
    """Offline platform health check via ``DSPPlatform.health_check``."""
    ready, status, checks = _platform_health(state)
    _append_infra_checks(state, checks)
    result = state.platform.health_check()
    meta = result.metadata
    components = collect_component_statuses(state, platform_ready=ready)
    platform_status = resolve_platform_status(
        platform_ready=ready, components=components
    )
    return HealthResponse(
        status=status,
        ready=ready,
        api_version=state.api_version,
        platform_version=meta.version,
        pipeline_version=COMPOSITION_PIPELINE_VERSION,
        repository_version=meta.version,
        checks=checks,
        limitations=list(result.limitations),
        components=components,
        platform_status=platform_status.value,
    )


@router.get("/health/live")
def health_live() -> JSONResponse:
    """Liveness probe — process is running (P1.3 lifecycle + build metadata)."""
    build = get_build_metadata()
    lifecycle = get_lifecycle_state()
    live_status = (
        "stopping"
        if lifecycle
        in {
            PlatformLifecycleState.SHUTTING_DOWN,
            PlatformLifecycleState.STOPPED,
        }
        else "alive"
    )
    return JSONResponse(
        {
            "status": live_status,
            "lifecycle": lifecycle.value,
            "application_version": build.application_version,
            "release_channel": build.release_channel,
        }
    )


@router.get("/health/ready")
def health_ready(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    """Readiness probe — platform and ops dependencies available."""
    platform_ready, status, checks = _platform_health(state)
    _append_infra_checks(state, checks)
    snapshot = collect_health_snapshot(state)
    components = collect_component_statuses(state, platform_ready=platform_ready)
    platform_status = resolve_platform_status(
        platform_ready=platform_ready, components=components
    )
    # Soft-fail: accept traffic when platform is ready even if optional copilot
    # or Redis are degraded (EPIC-011A).
    copilot_ok = bool(snapshot.get("service_readiness", {}).get("copilot_service"))
    accept = platform_ready or copilot_ok
    snapshot["status"] = "pass" if accept and platform_ready else status
    snapshot["ready"] = accept
    snapshot["platform_ready"] = platform_ready
    snapshot["platform_status"] = platform_status.value
    snapshot["lifecycle"] = get_lifecycle_state().value
    snapshot["checks"] = checks
    snapshot["components"] = components
    snapshot["service_readiness"]["accepting_traffic"] = accept
    # P1.3: ready|degraded → 200; unhealthy|startup|shutdown → 503
    if platform_status in {
        PlatformLifecycleState.UNHEALTHY,
        PlatformLifecycleState.STARTUP,
        PlatformLifecycleState.SHUTTING_DOWN,
        PlatformLifecycleState.STOPPED,
    }:
        code = 503
    else:
        code = 200 if accept else 503
    return JSONResponse(snapshot, status_code=code)


@router.get("/health/startup")
def health_startup(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    """RC1 M10 — startup probe via production_ops aggregation."""
    from api_platform.api.production_ops_wiring import build_production_ops_deps

    result = state.platform.run_production_ops(
        "startup", api_state=state, deps=build_production_ops_deps()
    )
    code = 200 if result.get("ok") and (result.get("result") or {}).get("started") else 503
    return JSONResponse(result, status_code=code)


@router.get("/health/dependencies")
def health_dependencies(state: ApiState = Depends(get_api_state)) -> JSONResponse:
    """RC1 M10 — dependency aggregation (reuses infra + platform probes)."""
    from api_platform.api.production_ops_wiring import build_production_ops_deps

    result = state.platform.run_production_ops(
        "dependencies", api_state=state, deps=build_production_ops_deps()
    )
    return JSONResponse(result, status_code=200 if result.get("ok") else 503)
