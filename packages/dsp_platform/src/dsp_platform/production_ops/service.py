"""RC1 Milestone 10 — Production Operations orchestration.

Aggregates existing health, metrics, logging, OTel, enterprise ops, and
backup interfaces. Never duplicates monitoring or invents KPIs.
"""

from __future__ import annotations

import os
import time
from typing import Any, Mapping

from dsp_platform.production_ops.deps import ProductionOpsDeps

UNAVAILABLE_MESSAGE = "Data unavailable."
PRODUCTION_OPS_SCHEMA_VERSION = "1.0.0"
PRODUCTION_OPS_SERVICE_VERSION = "0.1.0"

_START = time.time()


def production_ops_schema() -> dict[str, Any]:
    return {
        "schema_version": PRODUCTION_OPS_SCHEMA_VERSION,
        "service_version": PRODUCTION_OPS_SERVICE_VERSION,
        "routes": [
            "/ops/health",
            "/ops/metrics",
            "/ops/status",
            "/ops/version",
            "/ops/dependencies",
            "/ops/schema",
            "/ops/backup",
            "/ops/secrets",
            "/ops/observability",
        ],
        "reuses": [
            "GET /health",
            "GET /health/live",
            "GET /health/ready",
            "GET /metrics",
            "production_platform.json_logging",
            "production_platform.otel_tracing",
            "production_platform.prometheus_metrics",
            "production_platform.correlation",
            "enterprise.operational_dashboard",
            "api_platform.ops.collect_health_snapshot",
            "BackupPort",
            "SecretRotationHookPort",
            "VaultSecretsProviderPort",
        ],
        "rules": [
            "orchestration_only",
            "no_duplicated_monitoring",
            "no_duplicated_logging",
            "no_duplicated_health_checks",
            "missing_is_data_unavailable",
            "never_hardcode_secrets",
        ],
    }


def run_production_ops(
    action: str,
    *,
    platform: Any = None,
    api_state: Any = None,
    payload: Mapping[str, Any] | None = None,
    deps: ProductionOpsDeps | None = None,
) -> dict[str, Any]:
    """Dispatch a production-ops action — aggregation only.

    Infra/HTTP helpers must be supplied via ``deps`` from the composition root
    (never imported from api_platform / production_platform here).
    """
    body = dict(payload or {})
    act = (action or "").strip().lower().replace("-", "_")
    handlers = {
        "schema": production_ops_schema,
        "health": lambda: _health(platform, api_state, deps),
        "live": lambda: _live(deps),
        "ready": lambda: _ready(platform, api_state),
        "startup": lambda: _startup(platform, api_state, deps),
        "status": lambda: _status(platform, api_state, deps),
        "version": lambda: _version(deps),
        "dependencies": lambda: _dependencies(platform, api_state),
        "metrics": lambda: _metrics_summary(deps),
        "observability": lambda: _observability(deps),
        "backup": lambda: _backup(body, deps),
        "secrets": lambda: _secrets(deps),
        "dashboard": lambda: _dashboard(platform, api_state, deps),
    }
    if act not in handlers:
        raise ValueError(f"Unknown production-ops action: {action!r}")
    try:
        result = handlers[act]()
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "action": act,
            "message": UNAVAILABLE_MESSAGE,
            "error": str(exc),
        }
    return {
        "ok": True,
        "action": act,
        "result": result,
        "message": None,
        "provenance": {
            "schema_version": PRODUCTION_OPS_SCHEMA_VERSION,
            "service_version": PRODUCTION_OPS_SERVICE_VERSION,
            "orchestration_only": True,
            "calculations_performed": False,
        },
    }


def _version(deps: ProductionOpsDeps | None = None) -> dict[str, Any]:
    getter = deps.get_build_metadata if deps is not None else None
    if getter is not None:
        try:
            build = getter()
            return {
                "application_version": build.application_version,
                "api_version": build.api_version,
                "platform_version": build.platform_version,
                "pipeline_version": build.pipeline_version,
                "git_sha": build.git_sha,
                "build_timestamp": build.build_timestamp,
                "environment": build.environment,
                "release_channel": build.release_channel,
                "uptime_seconds": round(time.time() - _START, 2),
            }
        except Exception:  # noqa: BLE001
            pass
    return {
        "application_version": os.environ.get("DSP_APP_VERSION", "unknown"),
        "git_sha": os.environ.get("GIT_SHA", "unknown"),
        "environment": os.environ.get("DSP_ENVIRONMENT", "development"),
        "message": UNAVAILABLE_MESSAGE,
    }


def _live(deps: ProductionOpsDeps | None = None) -> dict[str, Any]:
    ver = _version(deps)
    return {
        "status": "alive",
        "probe": "live",
        "application_version": ver.get("application_version"),
        "release_channel": ver.get("release_channel"),
    }


def _platform_ready(platform: Any) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    if platform is None:
        return False, [{"name": "platform", "status": "fail", "message": UNAVAILABLE_MESSAGE}]
    try:
        result = platform.health_check()
        ready = bool(result.ok)
        payload = result.payload
        if payload is not None:
            ready = bool(getattr(payload, "ready", ready))
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
        return ready, checks
    except Exception as exc:  # noqa: BLE001
        return False, [{"name": "platform", "status": "fail", "message": str(exc)}]


def _infra_probes(api_state: Any) -> dict[str, Any]:
    infra = getattr(api_state, "infrastructure", None) if api_state else None
    if infra is None or not hasattr(infra, "health_checks"):
        return {}
    try:
        return dict(infra.health_checks())
    except Exception:  # noqa: BLE001
        return {"error": UNAVAILABLE_MESSAGE}


def _ready(platform: Any, api_state: Any) -> dict[str, Any]:
    ready, checks = _platform_ready(platform)
    probes = _infra_probes(api_state)
    if probes:
        checks.append(
            {
                "name": "database",
                "status": "pass" if probes.get("database") else "fail",
                "message": f"adapter={probes.get('database_adapter', 'unknown')}",
            }
        )
        redis = probes.get("redis") or {}
        if isinstance(redis, dict):
            checks.append(
                {
                    "name": "cache",
                    "status": str(redis.get("status", "skip")),
                    "message": str(redis.get("fallback_active")),
                }
            )
    return {
        "probe": "ready",
        "ready": ready,
        "status": "pass" if ready else "fail",
        "checks": checks,
        "dependencies": probes or {"message": UNAVAILABLE_MESSAGE},
    }


def _startup(
    platform: Any,
    api_state: Any,
    deps: ProductionOpsDeps | None = None,
) -> dict[str, Any]:
    lifecycle_value = "unknown"
    getter = deps.get_lifecycle_state if deps is not None else None
    if getter is not None:
        try:
            lifecycle = getter()
            lifecycle_value = getattr(lifecycle, "value", str(lifecycle))
        except Exception:  # noqa: BLE001
            lifecycle_value = "unknown"

    ready, checks = _platform_ready(platform)
    startup_ok = lifecycle_value not in {"unhealthy", "stopped", "shutting_down"}
    return {
        "probe": "startup",
        "lifecycle": lifecycle_value,
        "started": startup_ok,
        "platform_ready": ready,
        "checks": checks,
        "accepting_traffic": ready and startup_ok,
        "infra_attached": getattr(api_state, "infrastructure", None) is not None
        if api_state
        else False,
    }


def _dependencies(platform: Any, api_state: Any) -> dict[str, Any]:
    probes = _infra_probes(api_state)
    ready, _ = _platform_ready(platform)

    def _comp(name: str, ok: bool | None, detail: str) -> dict[str, Any]:
        if ok is None:
            return {"name": name, "status": "skip", "message": detail or UNAVAILABLE_MESSAGE}
        return {
            "name": name,
            "status": "pass" if ok else "fail",
            "message": detail or ("ok" if ok else UNAVAILABLE_MESSAGE),
        }

    components = [
        _comp("platform", ready, "DSPPlatform.health_check"),
        _comp(
            "database",
            bool(probes.get("database")) if probes else None,
            str(probes.get("database_adapter", UNAVAILABLE_MESSAGE)),
        ),
        _comp(
            "cache",
            None
            if not probes
            else str((probes.get("redis") or {}).get("status", "skip")) == "pass",
            str(probes.get("cache_adapter", UNAVAILABLE_MESSAGE)),
        ),
        _comp(
            "connectors",
            None,
            "Data Connector Framework — probe via domain /health routes",
        ),
        _comp(
            "workflow",
            None,
            "Institutional Workflow — availability via platform methods",
        ),
        _comp(
            "ai_copilot",
            getattr(api_state, "copilot_service", None) is not None
            if api_state
            else None,
            "copilot_service wiring",
        ),
        _comp(
            "portfolio",
            None,
            "Portfolio Intelligence — engine reuse, no duplicate probe",
        ),
        _comp(
            "research",
            ready,
            "Company / Research Workspace via platform readiness",
        ),
        _comp(
            "saas",
            None,
            "SaaS Platform orchestration — enterprise domain",
        ),
    ]
    return {
        "components": components,
        "raw_infra": probes or {"message": UNAVAILABLE_MESSAGE},
        "note": "Dependency aggregation only — reuses existing probes.",
    }


def _health(
    platform: Any,
    api_state: Any,
    deps: ProductionOpsDeps | None = None,
) -> dict[str, Any]:
    return {
        "live": _live(deps),
        "ready": _ready(platform, api_state),
        "startup": _startup(platform, api_state, deps),
        "dependencies": _dependencies(platform, api_state),
        "version": _version(deps),
    }


def _status(
    platform: Any,
    api_state: Any,
    deps: ProductionOpsDeps | None = None,
) -> dict[str, Any]:
    collect_statuses = deps.collect_component_statuses if deps is not None else None
    resolve_status = deps.resolve_platform_status if deps is not None else None
    collect_snapshot = deps.collect_health_snapshot if deps is not None else None
    if collect_statuses is not None and resolve_status is not None:
        try:
            ready, _ = _platform_ready(platform)
            components = collect_statuses(api_state, platform_ready=ready)
            lifecycle = resolve_status(platform_ready=ready, components=components)
            snapshot = (
                collect_snapshot(api_state)
                if collect_snapshot is not None and api_state
                else {}
            )
            return {
                "lifecycle": getattr(lifecycle, "value", str(lifecycle)),
                "platform_ready": ready,
                "components": components,
                "snapshot": snapshot,
                "observability": _observability(deps),
            }
        except Exception as exc:  # noqa: BLE001
            ready, checks = _platform_ready(platform)
            return {
                "lifecycle": "unknown",
                "platform_ready": ready,
                "checks": checks,
                "message": UNAVAILABLE_MESSAGE,
                "error": str(exc),
            }
    ready, checks = _platform_ready(platform)
    return {
        "lifecycle": "unknown",
        "platform_ready": ready,
        "checks": checks,
        "message": UNAVAILABLE_MESSAGE,
    }


def _metrics_summary(deps: ProductionOpsDeps | None = None) -> dict[str, Any]:
    """Summary pointer to Prometheus /metrics — does not duplicate scrape payload."""
    render = deps.render_prometheus if deps is not None else None
    if render is not None:
        try:
            text = render()
            lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
            return {
                "available": True,
                "scrape_path": "/metrics",
                "ops_alias": "/ops/metrics",
                "sample_series_count": len(lines),
                "note": (
                    "Full exposition at GET /metrics (Prometheus). "
                    "Ops alias returns this summary + text."
                ),
                "prometheus_text_preview": "\n".join(lines[:40]),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "available": False,
                "scrape_path": "/metrics",
                "message": UNAVAILABLE_MESSAGE,
                "error": str(exc),
            }
    return {
        "available": False,
        "scrape_path": "/metrics",
        "message": UNAVAILABLE_MESSAGE,
    }


def _observability(deps: ProductionOpsDeps | None = None) -> dict[str, Any]:
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT") or os.environ.get(
        "DSP_OTEL_ENDPOINT"
    )
    tracing_available = False
    try_build = deps.try_build_otel_tracing if deps is not None else None
    if try_build is not None:
        try:
            tracing_available = try_build() is not None
        except Exception:  # noqa: BLE001
            tracing_available = False

    corr = None
    get_corr = deps.get_correlation_id if deps is not None else None
    if get_corr is not None:
        try:
            corr = get_corr()
        except Exception:  # noqa: BLE001
            corr = None

    return {
        "structured_logging": {
            "available": True,
            "format": "json",
            "modules": [
                "production_platform.production.json_logging",
                "api_platform.api.monitoring.ops_logger",
            ],
            "fields": [
                "request_id",
                "correlation_id",
                "trace_id",
                "module",
                "latency_ms",
                "error",
            ],
        },
        "opentelemetry": {
            "available": bool(tracing_available or otel_endpoint),
            "endpoint": otel_endpoint or None,
            "message": None
            if (tracing_available or otel_endpoint)
            else "OpenTelemetry exporter unavailable.",
            "spans": [
                "api",
                "database",
                "copilot",
                "workflow",
                "portfolio",
                "company_analysis",
            ],
        },
        "prometheus": {
            "available": True,
            "path": "/metrics",
            "grafana_dashboards": [
                "docker/grafana/dashboards/dsp-operations.json",
                "deploy/observability/grafana/dashboards/dsp-production-health.json",
            ],
        },
        "correlation_id": corr,
        "audit": {
            "reuses": [
                "production_platform.audit_events",
                "security_platform.audit",
                "enterprise.record_audit",
            ]
        },
    }


def _backup(
    body: dict[str, Any],
    deps: ProductionOpsDeps | None = None,
) -> dict[str, Any]:
    adapter = deps.backup_adapter if deps is not None else None
    action = str(body.get("backup_action") or "status").lower()
    if adapter is None:
        payload: dict[str, Any] = {
            "available": False,
            "message": UNAVAILABLE_MESSAGE,
        }
        if action in {"create", "restore"}:
            payload["ok"] = False
        return payload
    if action == "list":
        return {
            "available": adapter.is_available(),
            "snapshots": adapter.list_snapshots(limit=int(body.get("limit") or 20)),
            "status": adapter.status(),
        }
    if action == "create":
        return adapter.create_snapshot(label=body.get("label"))
    if action == "restore":
        return adapter.restore_snapshot(str(body.get("snapshot_id") or ""))
    return adapter.status()


def _secrets(deps: ProductionOpsDeps | None = None) -> dict[str, Any]:
    rotation = {"available": False, "message": UNAVAILABLE_MESSAGE}
    vault = {"available": False, "message": UNAVAILABLE_MESSAGE}
    if deps is not None:
        try:
            if deps.secret_rotation_hook is not None:
                rotation = deps.secret_rotation_hook.rotation_status()
            if deps.vault_secrets_provider is not None:
                vault = deps.vault_secrets_provider.status()
        except Exception:  # noqa: BLE001
            rotation = {"available": False, "message": UNAVAILABLE_MESSAGE}
            vault = {"available": False, "message": UNAVAILABLE_MESSAGE}

    env_validation = {
        "script": "scripts/validate_env.py",
        "secrets_port": "production_platform.production.configuration.EnvSecretsPort",
        "never_hardcode": True,
    }
    return {
        "rotation": rotation,
        "vault": vault,
        "environment_validation": env_validation,
        "note": "Interfaces only until Vault/KMS is configured.",
    }


def _dashboard(
    platform: Any,
    api_state: Any,
    deps: ProductionOpsDeps | None = None,
) -> dict[str, Any]:
    """Admin production ops dashboard — honest aggregates."""
    enterprise_ops = None
    try:
        from enterprise import get_enterprise_service

        enterprise_ops = get_enterprise_service().operational_dashboard(
            infrastructure=getattr(api_state, "infrastructure", None)
            if api_state
            else None
        )
    except Exception:  # noqa: BLE001
        enterprise_ops = {"available": False, "message": UNAVAILABLE_MESSAGE}

    return {
        "health": _health(platform, api_state, deps),
        "version": _version(deps),
        "observability": _observability(deps),
        "metrics": _metrics_summary(deps),
        "backup": _backup({"backup_action": "status"}, deps),
        "secrets": _secrets(deps),
        "enterprise_ops": enterprise_ops,
        "security_hardening": {
            "headers": "api_platform.ops_middleware.SecurityHeadersMiddleware",
            "cors": "DSP_CORS_ORIGINS",
            "rate_limits": "RateLimitHookMiddleware + production_platform.rate_limit",
            "edge": "docker/Caddyfile",
        },
        "ci_cd": {
            "workflows": [
                ".github/workflows/ci.yml",
                ".github/workflows/frontend.yml",
                ".github/workflows/security.yml",
                ".github/workflows/docker.yml",
                ".github/workflows/release-engineering.yml",
                ".github/workflows/rc-production-ops.yml",
            ]
        },
    }
