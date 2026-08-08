"""Read-only operational viewers (EPIC-A010)."""

from __future__ import annotations

import importlib
import os
from typing import Any

from admin.models import UNAVAILABLE_MESSAGE

__all__ = [
    "ConfigViewer",
    "FeatureFlagViewer",
    "HealthPanel",
    "MetricsViewer",
    "VersionViewer",
]

_KNOWN_PACKAGES = (
    "dsp_platform",
    "api_platform",
    "persistence",
    "auth",
    "admin",
    "security_platform",
    "production_platform",
    "compliance",
    "research",
    "valuation",
    "financial",
    "workflow",
)


class HealthPanel:
    """Static readiness from existing services — no engine execution."""

    def __init__(self, persistence_service: Any, auth_service: Any) -> None:
        self._persistence = persistence_service
        self._auth = auth_service

    def snapshot(self) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        try:
            pschema = self._persistence.schema()
            checks.append(
                {
                    "name": "persistence",
                    "status": "pass",
                    "message": f"provider={pschema.get('provider')}",
                }
            )
        except Exception as exc:  # noqa: BLE001
            checks.append(
                {"name": "persistence", "status": "fail", "message": str(exc)}
            )
        try:
            aschema = self._auth.schema()
            checks.append(
                {
                    "name": "auth",
                    "status": "pass",
                    "message": f"roles={len(aschema.get('roles') or [])}",
                }
            )
        except Exception as exc:  # noqa: BLE001
            checks.append({"name": "auth", "status": "fail", "message": str(exc)})
        checks.append(
            {
                "name": "admin_console",
                "status": "pass",
                "message": "read_only_operational_visibility",
            }
        )
        ready = all(c["status"] == "pass" for c in checks)
        return {
            "status": "pass" if ready else "fail",
            "ready": ready,
            "checks": checks,
            "rules": [
                "no_engine_execution",
                "no_provider_calls",
                "no_research_mutation",
            ],
        }


class ConfigViewer:
    """Non-secret configuration key inventory (values redacted for secrets)."""

    _SECRET_MARKERS = ("SECRET", "PASSWORD", "TOKEN", "KEY", "CREDENTIAL")

    def snapshot(self) -> dict[str, Any]:
        keys = sorted(k for k in os.environ if k.startswith("DSP_"))
        items: list[dict[str, Any]] = []
        for key in keys:
            secret = any(m in key.upper() for m in self._SECRET_MARKERS)
            items.append(
                {
                    "key": key,
                    "set": True,
                    "value": UNAVAILABLE_MESSAGE if secret else os.environ.get(key),
                    "secret": secret,
                }
            )
        return {
            "source": "environ_DSP_prefix",
            "count": len(items),
            "items": items,
            "message": None if items else UNAVAILABLE_MESSAGE,
        }


class VersionViewer:
    def snapshot(self) -> dict[str, Any]:
        packages: list[dict[str, Any]] = []
        for name in _KNOWN_PACKAGES:
            try:
                mod = importlib.import_module(name)
                ver = getattr(mod, "__version__", None)
                if ver is None and name == "dsp_platform":
                    # pyproject is authoritative for epic versioning
                    try:
                        from importlib.metadata import version as pkg_version

                        ver = pkg_version("dsp_platform")
                    except Exception:  # noqa: BLE001
                        ver = UNAVAILABLE_MESSAGE
                packages.append(
                    {
                        "package": name,
                        "version": ver if ver is not None else UNAVAILABLE_MESSAGE,
                    }
                )
            except Exception:  # noqa: BLE001
                packages.append(
                    {"package": name, "version": UNAVAILABLE_MESSAGE}
                )
        return {"packages": packages}


class FeatureFlagViewer:
    def snapshot(self, flags: dict[str, bool] | None = None) -> dict[str, Any]:
        if flags is not None:
            ordered = {k: flags[k] for k in sorted(flags)}
            return {"source": "provided", "flags": ordered}
        try:
            from production_platform import FeatureFlagManager

            mgr = FeatureFlagManager()
            return {"source": "production_platform", "flags": mgr.as_dict()}
        except Exception:  # noqa: BLE001
            return {
                "source": "unavailable",
                "flags": {},
                "message": UNAVAILABLE_MESSAGE,
            }


class MetricsViewer:
    """System metrics from metadata counts — no scoring/valuation."""

    def __init__(self, persistence_service: Any, auth_service: Any) -> None:
        self._persistence = persistence_service
        self._auth = auth_service

    def snapshot(self) -> dict[str, Any]:
        def _count(kind: str) -> int:
            try:
                return len(self._persistence.list_ids(kind))
            except Exception:  # noqa: BLE001
                return 0

        sessions = 0
        active = 0
        try:
            for entity_id in self._persistence.list_ids("metadata"):
                if not str(entity_id).startswith("auth-session-"):
                    continue
                sessions += 1
                sid = str(entity_id)[len("auth-session-") :]
                session = self._auth.sessions.get(sid)
                if session is not None and not session.revoked:
                    active += 1
        except Exception:  # noqa: BLE001
            pass

        return {
            "users": len(self._auth.list_users()),
            "sessions_total": sessions,
            "sessions_active": active,
            "audit_records": _count("audit_record"),
            "workflow_records": _count("workflow_record"),
            "approval_history": _count("approval_history"),
            "research_refs": _count("research_ref"),
            "citations": _count("citation"),
            "provenance": _count("provenance"),
            "metadata_entities": _count("metadata"),
        }
