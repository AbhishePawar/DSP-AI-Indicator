"""Operations metadata — build info, probes, metrics (EPIC-013 RC1)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "BuildMetadata",
    "MetricsRegistry",
    "collect_health_snapshot",
    "get_build_metadata",
    "metrics_registry",
]

_START_TIME = time.time()
_REQUEST_COUNT = 0
_ERROR_COUNT = 0


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
        application_version=os.environ.get("DSP_APP_VERSION", "1.0.0-rc1"),
        api_version=os.environ.get("DSP_API_VERSION", "v1"),
        platform_version=os.environ.get("DSP_PLATFORM_VERSION", "0.2.0"),
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


def collect_health_snapshot(state: Any) -> dict[str, Any]:
    """Collect non-blocking operational health — no business logic."""
    build = get_build_metadata()
    llm_status = _llm_availability(state)
    providers = _provider_status(state)
    uptime_seconds = round(time.time() - _START_TIME, 2)

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
        }
        self._gauges: dict[str, float] = {
            "dsp_uptime_seconds": 0,
        }

    def inc_requests(self) -> None:
        self._counters["dsp_http_requests_total"] += 1

    def inc_errors(self) -> None:
        self._counters["dsp_http_errors_total"] += 1

    def render_prometheus(self) -> str:
        self._gauges["dsp_uptime_seconds"] = round(time.time() - _START_TIME, 2)
        lines: list[str] = []
        for name, value in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in self._gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
        build = get_build_metadata()
        lines.append("# TYPE dsp_build_info gauge")
        lines.append(
            f'dsp_build_info{{version="{build.application_version}",'
            f'env="{build.environment}"}} 1'
        )
        return "\n".join(lines) + "\n"


metrics_registry = MetricsRegistry()
