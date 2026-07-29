"""Operations metadata — build info, probes, metrics (EPIC-013 RC1 + P1.3)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from api_platform.api.monitoring import (
    PlatformLifecycleState,
    get_lifecycle_state,
    get_resource_snapshot,
)

__all__ = [
    "BuildMetadata",
    "MetricsRegistry",
    "collect_component_statuses",
    "collect_health_snapshot",
    "get_build_metadata",
    "metrics_registry",
    "resolve_platform_status",
]

_START_TIME = time.time()


@dataclass(frozen=True, slots=True)
class BuildMetadata:
    application_version: str
    api_version: str
    platform_version: str
    pipeline_version: str
    git_sha: str
    build_timestamp: str
    environment: str
    release_channel: str


def get_build_metadata() -> BuildMetadata:
    return BuildMetadata(
        application_version=os.environ.get("DSP_APP_VERSION", "1.6.0"),
        api_version=os.environ.get("DSP_API_VERSION", "v1"),
        platform_version=os.environ.get("DSP_PLATFORM_VERSION", "1.6.0"),
        pipeline_version=os.environ.get(
            "DSP_PIPELINE_VERSION", "1.0.0-epic-001"
        ),
        git_sha=os.environ.get("GIT_SHA", os.environ.get("GITHUB_SHA", "unknown")),
        build_timestamp=os.environ.get(
            "BUILD_TIMESTAMP", os.environ.get("DSP_BUILD_TIMESTAMP", "unknown")
        ),
        environment=os.environ.get("DSP_ENVIRONMENT", "development"),
        release_channel=os.environ.get("DSP_RELEASE_CHANNEL", "rc1"),
    )


def collect_component_statuses(
    state: Any, *, platform_ready: bool
) -> dict[str, dict[str, str]]:
    """Structured component health — Unavailable/skip when not wired."""
    lifecycle = get_lifecycle_state()
    security_on = os.environ.get("DSP_ENABLE_SECURITY", "").lower() in {
        "1",
        "true",
        "yes",
    }
    has_api = state is not None
    has_copilot = getattr(state, "copilot_service", None) is not None

    # Database / storage: report configured adapters only — no inventing connectivity.
    db = os.environ.get("DSP_DATABASE_URL") or os.environ.get("DATABASE_URL")
    storage = os.environ.get("DSP_STORAGE_BACKEND") or os.environ.get(
        "DSP_PERSISTENCE_BACKEND"
    )

    def status(ok: bool, *, skip: bool = False, message: str = "") -> dict[str, str]:
        if skip:
            return {"status": "skip", "message": message or "Unavailable"}
        return {
            "status": "pass" if ok else "fail",
            "message": message or ("ok" if ok else "unhealthy"),
        }

    return {
        "application": status(
            lifecycle
            not in {
                PlatformLifecycleState.UNHEALTHY,
                PlatformLifecycleState.STOPPED,
            },
            message=f"lifecycle={lifecycle.value}",
        ),
        "api": status(has_api, message="api_state"),
        "authentication": status(
            True,
            skip=not security_on and not os.environ.get("DSP_JWT_SECRET"),
            message="security_enabled" if security_on else "optional",
        ),
        "database": status(
            True,
            skip=db is None,
            message="configured" if db else "Unavailable",
        ),
        "storage": status(
            True,
            skip=storage is None,
            message="configured" if storage else "Unavailable",
        ),
        "research_service": status(
            platform_ready,
            message="platform_health" if platform_ready else "platform_not_ready",
        ),
        "overall": status(
            platform_ready and has_api,
            message="aggregate",
        ),
        "copilot": status(
            has_copilot,
            skip=False,
            message="wired" if has_copilot else "Unavailable",
        ),
    }


def resolve_platform_status(
    *,
    platform_ready: bool,
    components: dict[str, dict[str, str]],
) -> PlatformLifecycleState:
    """Map component checks → startup|ready|degraded|unhealthy."""
    lifecycle = get_lifecycle_state()
    if lifecycle in {
        PlatformLifecycleState.SHUTTING_DOWN,
        PlatformLifecycleState.STOPPED,
    }:
        return lifecycle
    if not platform_ready or components.get("api", {}).get("status") == "fail":
        return PlatformLifecycleState.UNHEALTHY
    if components.get("copilot", {}).get("status") != "pass":
        return PlatformLifecycleState.DEGRADED
    if lifecycle == PlatformLifecycleState.STARTUP:
        return PlatformLifecycleState.STARTUP
    return PlatformLifecycleState.READY


def collect_health_snapshot(state: Any) -> dict[str, Any]:
    """Collect non-blocking operational health — no business logic."""
    build = get_build_metadata()
    llm_status = _llm_availability(state)
    providers = _provider_status(state)
    uptime_seconds = round(time.time() - _START_TIME, 2)
    resources = get_resource_snapshot()

    return {
        "status": "pass",
        "ready": True,
        "application_version": build.application_version,
        "api_version": build.api_version,
        "platform_version": build.platform_version,
        "pipeline_version": build.pipeline_version,
        "build": {
            "git_sha": build.git_sha,
            "build_timestamp": build.build_timestamp,
            "environment": build.environment,
            "release_channel": build.release_channel,
        },
        "uptime_seconds": uptime_seconds,
        "providers": providers,
        "llm": llm_status,
        "resources": resources,
        "service_readiness": {
            "platform": True,
            "copilot_service": state.copilot_service is not None,
            "api_state": state is not None,
        },
    }


def _llm_availability(state: Any) -> dict[str, Any]:
    """Non-blocking LLM probe — reports configuration only."""
    try:
        service = getattr(state, "copilot_service", None)
        if service is None:
            return {"available": False, "active_provider": "none", "blocking": False}
        active = service.active_provider_id()
        registry = service._registry  # noqa: SLF001 — ops probe only
        providers = registry.list_providers()
        configured = [p for p in providers if p.get("configured")]
        return {
            "available": len(configured) > 0,
            "active_provider": active,
            "configured_providers": [p["id"] for p in configured],
            "blocking": False,
        }
    except Exception as exc:  # pragma: no cover - defensive ops
        return {
            "available": False,
            "active_provider": "unknown",
            "blocking": False,
            "note": str(exc),
        }


def _provider_status(state: Any) -> dict[str, Any]:
    try:
        service = getattr(state, "copilot_service", None)
        if service is None:
            return {"copilot": "unavailable"}
        return {"copilot": service.list_providers()}
    except Exception:
        return {"copilot": "unavailable"}


class MetricsRegistry:
    """In-process Prometheus-compatible metrics registry."""

    def __init__(self) -> None:
        self._counters: dict[str, float] = {
            "dsp_http_requests_total": 0,
            "dsp_http_errors_total": 0,
            "dsp_analysis_requests_total": 0,
            "dsp_analysis_failures_total": 0,
            "dsp_research_requests_total": 0,
            "dsp_export_requests_total": 0,
            "dsp_auth_failures_total": 0,
            "dsp_authz_denials_total": 0,
            "dsp_rate_limit_events_total": 0,
            "dsp_system_restarts_total": 0,
        }
        self._gauges: dict[str, float] = {
            "dsp_uptime_seconds": 0,
            "dsp_api_latency_ms_last": 0,
            "dsp_analysis_duration_ms_last": 0,
            "dsp_research_duration_ms_last": 0,
            "dsp_export_duration_ms_last": 0,
        }
        self._latency_sum_ms = 0.0
        self._latency_count = 0

    def inc_requests(self) -> None:
        self._counters["dsp_http_requests_total"] += 1

    def inc_errors(self) -> None:
        self._counters["dsp_http_errors_total"] += 1

    def observe_latency_ms(self, elapsed_ms: float) -> None:
        self._gauges["dsp_api_latency_ms_last"] = round(elapsed_ms, 2)
        self._latency_sum_ms += elapsed_ms
        self._latency_count += 1

    def inc(self, name: str, amount: float = 1) -> None:
        if name in self._counters:
            self._counters[name] += amount

    def set_gauge(self, name: str, value: float) -> None:
        if name in self._gauges:
            self._gauges[name] = value

    def note_path(self, path: str, *, status_code: int, elapsed_ms: float) -> None:
        """Classify operational counters from path — no business logic."""
        self.observe_latency_ms(elapsed_ms)
        lower = path.lower()
        if "/analyse" in lower or "/analyze" in lower:
            self.inc("dsp_analysis_requests_total")
            self.set_gauge("dsp_analysis_duration_ms_last", round(elapsed_ms, 2))
            if status_code >= 400:
                self.inc("dsp_analysis_failures_total")
        if "/research" in lower:
            self.inc("dsp_research_requests_total")
            self.set_gauge("dsp_research_duration_ms_last", round(elapsed_ms, 2))
        if "/export" in lower:
            self.inc("dsp_export_requests_total")
            self.set_gauge("dsp_export_duration_ms_last", round(elapsed_ms, 2))
        if status_code == 401:
            self.inc("dsp_auth_failures_total")
        if status_code == 403:
            self.inc("dsp_authz_denials_total")
        if status_code == 429:
            self.inc("dsp_rate_limit_events_total")

    def render_prometheus(self) -> str:
        self._gauges["dsp_uptime_seconds"] = round(time.time() - _START_TIME, 2)
        lines: list[str] = []
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        if self._latency_count:
            avg = self._latency_sum_ms / self._latency_count
            lines.append("# TYPE dsp_api_latency_ms_avg gauge")
            lines.append(f"dsp_api_latency_ms_avg {round(avg, 2)}")
        build = get_build_metadata()
        lines.append("# TYPE dsp_build_info gauge")
        lines.append(
            f'dsp_build_info{{version="{build.application_version}",'
            f'env="{build.environment}"}} 1'
        )
        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
