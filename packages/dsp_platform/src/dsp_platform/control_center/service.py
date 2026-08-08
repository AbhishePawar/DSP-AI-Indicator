"""RC1 Milestone 11 — Super Admin Control Center orchestration.

Configuration registry + façades over admin / saas / ops / AI / connectors.
Never executes valuation, risk, or recommendation engines.
"""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.control_center.defaults import MODULE_IDS
from dsp_platform.control_center.registry import get_configuration_registry

UNAVAILABLE_MESSAGE = "Data unavailable."
CONTROL_CENTER_SCHEMA_VERSION = "1.0.0"
CONTROL_CENTER_SERVICE_VERSION = "0.1.0"


def control_center_schema() -> dict[str, Any]:
    return {
        "schema_version": CONTROL_CENTER_SCHEMA_VERSION,
        "service_version": CONTROL_CENTER_SERVICE_VERSION,
        "modules": list(MODULE_IDS),
        "routes": [
            "/admin/control-center/schema",
            "/admin/configuration/registry",
            "/admin/configuration",
            "/admin/configuration/history",
            "/admin/rollback",
            "/admin/branding",
            "/admin/cms",
            "/admin/feature-flags/overrides",
            "/admin/valuation/config",
            "/admin/ai/config",
            "/admin/risk/config",
            "/admin/market/config",
            "/admin/connectors/config",
            "/admin/business-rules",
            "/admin/notifications/config",
            "/admin/dashboard/layout",
            "/admin/security/config",
            "/admin/templates/config",
            "/admin/saas/control",
            "/admin/monitoring",
            "/admin/backup/control",
            "/admin/release",
            "/admin/audit/config",
        ],
        "rules": [
            "orchestration_only",
            "config_overlays_only",
            "never_execute_engines",
            "no_duplicated_authentication",
            "no_duplicated_valuation",
            "no_duplicated_monitoring",
            "reuse_admin_saas_ops",
            "missing_is_data_unavailable",
        ],
        "reuses": [
            "admin_facade",
            "saas_platform",
            "production_ops",
            "enterprise",
            "copilot_providers",
            "data_connector_framework",
            "feature_flags",
            "audit_logger",
        ],
    }


def run_control_center(
    action: str,
    *,
    platform: Any = None,
    api_state: Any = None,
    payload: Mapping[str, Any] | None = None,
    ops_deps: Any = None,
) -> dict[str, Any]:
    body = dict(payload or {})
    act = (action or "").strip().lower().replace("-", "_")
    registry = get_configuration_registry()

    handlers = {
        "schema": control_center_schema,
        "get_registry": lambda: {"modules": registry.get_all()},
        "get_module": lambda: _get_module(registry, body),
        "update_configuration": lambda: _update(registry, body, platform),
        "history": lambda: {
            "history": registry.history(
                module_id=body.get("module_id"),
                limit=int(body.get("limit") or 50),
            )
        },
        "rollback": lambda: _rollback(registry, body, platform),
        "branding": lambda: _module_write(registry, "branding", body, platform),
        "cms": lambda: _cms(registry, body, platform),
        "feature_flags": lambda: _feature_flags(registry, body, platform),
        "valuation": lambda: _module_write(registry, "valuation", body, platform),
        "ai": lambda: _ai(registry, body, platform),
        "risk": lambda: _module_write(registry, "risk", body, platform),
        "market": lambda: _module_write(registry, "market", body, platform),
        "connectors": lambda: _module_write(registry, "connectors", body, platform),
        "notifications": lambda: _module_write(
            registry, "notifications", body, platform
        ),
        "dashboard_layout": lambda: _module_write(
            registry, "dashboard", body, platform
        ),
        "security": lambda: _module_write(registry, "security", body, platform),
        "templates": lambda: _module_write(registry, "templates", body, platform),
        "saas_control": lambda: _saas_control(registry, body, platform),
        "business_rules_list": lambda: {"rules": registry.list_rules()},
        "business_rules_upsert": lambda: {
            "rule": registry.upsert_rule(body, author=_author(body))
        },
        "business_rules_delete": lambda: {
            "deleted": registry.delete_rule(
                str(body.get("rule_id") or ""), author=_author(body)
            )
        },
        "monitoring": lambda: _monitoring(platform, api_state, ops_deps),
        "backup": lambda: _backup(platform, api_state, body, ops_deps),
        "release": lambda: _release(platform, api_state, registry, ops_deps),
        "audit": lambda: {
            "audit": registry.export_audit(limit=int(body.get("limit") or 200))
        },
        "users_orgs": lambda: _users_orgs(platform),
        "dashboard": lambda: _control_dashboard(
            platform, api_state, registry, ops_deps
        ),
    }
    if act not in handlers:
        raise ValueError(f"Unknown control-center action: {action!r}")
    try:
        result = handlers[act]()
    except ValueError:
        raise
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
            "schema_version": CONTROL_CENTER_SCHEMA_VERSION,
            "service_version": CONTROL_CENTER_SERVICE_VERSION,
            "orchestration_only": True,
            "engines_executed": False,
        },
    }


def _author(body: dict[str, Any]) -> str:
    return str(body.get("author") or body.get("actor_user_id") or "admin")


def _get_module(registry: Any, body: dict[str, Any]) -> dict[str, Any]:
    mid = str(body.get("module_id") or "")
    cfg = registry.get_module(mid)
    if cfg is None:
        raise ValueError("module not found")
    return {"module_id": mid, "configuration": cfg}


def _audit_enterprise(platform: Any, body: dict[str, Any], change: dict[str, Any]) -> None:
    if platform is None:
        return
    try:
        from enterprise import get_enterprise_service

        get_enterprise_service().record_audit(
            org_id=body.get("org_id"),
            actor_user_id=_author(body),
            action="control_center.config_change",
            resource_type="configuration",
            resource_id=str(change.get("module_id")),
            metadata={
                "version": change.get("version"),
                "reason": change.get("reason"),
                "change_id": change.get("change_id"),
            },
        )
    except Exception:  # noqa: BLE001
        pass


def _update(registry: Any, body: dict[str, Any], platform: Any) -> dict[str, Any]:
    module_id = str(body.get("module_id") or "")
    patch = dict(body.get("configuration") or body.get("patch") or {})
    if not module_id:
        raise ValueError("module_id required")
    if not patch:
        raise ValueError("configuration patch required")
    result = registry.update_module(
        module_id,
        patch,
        author=_author(body),
        reason=body.get("reason"),
        approval_status=str(body.get("approval_status") or "approved"),
        replace=bool(body.get("replace")),
    )
    _audit_enterprise(platform, body, result.get("change") or {})
    return result


def _rollback(registry: Any, body: dict[str, Any], platform: Any) -> dict[str, Any]:
    version = int(body.get("version") or 0)
    result = registry.rollback(
        version, author=_author(body), reason=body.get("reason")
    )
    _audit_enterprise(platform, body, result.get("change") or {})
    return result


def _module_write(
    registry: Any, module_id: str, body: dict[str, Any], platform: Any
) -> dict[str, Any]:
    patch = dict(body.get("configuration") or body.get("patch") or body)
    # Strip control fields
    for key in (
        "module_id",
        "author",
        "actor_user_id",
        "reason",
        "approval_status",
        "replace",
        "configuration",
        "patch",
    ):
        patch.pop(key, None)
    result = registry.update_module(
        module_id,
        patch,
        author=_author(body),
        reason=body.get("reason"),
        approval_status=str(body.get("approval_status") or "approved"),
        replace=bool(body.get("replace")),
    )
    _audit_enterprise(platform, body, result.get("change") or {})
    return result


def _cms(registry: Any, body: dict[str, Any], platform: Any) -> dict[str, Any]:
    page_id = body.get("page_id")
    if page_id:
        pages = dict((registry.get_module("cms") or {}).get("pages") or {})
        page = dict(pages.get(str(page_id)) or {"title": str(page_id), "body": ""})
        if body.get("title") is not None:
            page["title"] = body["title"]
        if body.get("body") is not None:
            page["body"] = body["body"]
        if body.get("published") is not None:
            page["published"] = bool(body["published"])
        pages[str(page_id)] = page
        return _module_write(
            registry,
            "cms",
            {
                **body,
                "configuration": {"pages": pages},
            },
            platform,
        )
    return _module_write(registry, "cms", body, platform)


def _feature_flags(registry: Any, body: dict[str, Any], platform: Any) -> dict[str, Any]:
    flags = dict(body.get("flags") or body.get("configuration") or {})
    if not flags and body.get("flag") is not None:
        flags = {str(body["flag"]): bool(body.get("enabled", True))}
    result = registry.update_module(
        "feature_flags",
        flags,
        author=_author(body),
        reason=body.get("reason") or "feature flag update",
    )
    _audit_enterprise(platform, body, result.get("change") or {})
    # Feature-flag overlays are owned by ConfigurationRegistry (ASI-003:
    # do not import production_platform FeatureFlagManager from dsp_platform).
    return result


def _ai(registry: Any, body: dict[str, Any], platform: Any) -> dict[str, Any]:
    # Strip any secret-looking keys
    patch = dict(body.get("configuration") or body.get("patch") or {})
    for secret_key in list(patch.keys()):
        lk = secret_key.lower()
        if any(s in lk for s in ("api_key", "secret", "password", "token")):
            patch.pop(secret_key, None)
    providers = None
    if platform is not None:
        try:
            # Read-only provider discovery — never invent keys
            if hasattr(platform, "copilot_providers"):
                providers = platform.copilot_providers()
        except Exception:  # noqa: BLE001
            providers = {"available": False, "message": UNAVAILABLE_MESSAGE}
    written = registry.update_module(
        "ai",
        patch,
        author=_author(body),
        reason=body.get("reason") or "ai config update",
        replace=bool(body.get("replace")),
    )
    _audit_enterprise(platform, body, written.get("change") or {})
    return {**written, "providers": providers}


def _saas_control(registry: Any, body: dict[str, Any], platform: Any) -> dict[str, Any]:
    written = _module_write(registry, "saas", body, platform)
    saas_snapshot = None
    if platform is not None:
        try:
            saas_snapshot = platform.run_saas_platform("plans")
        except Exception:  # noqa: BLE001
            saas_snapshot = {"ok": False, "message": UNAVAILABLE_MESSAGE}
    return {**written, "saas_plans": saas_snapshot}


def _monitoring(
    platform: Any,
    api_state: Any,
    ops_deps: Any = None,
) -> dict[str, Any]:
    ops = None
    admin_metrics = None
    if platform is not None:
        try:
            ops = platform.run_production_ops(
                "dashboard", api_state=api_state, deps=ops_deps
            )
        except Exception:  # noqa: BLE001
            ops = {"ok": False, "message": UNAVAILABLE_MESSAGE}
        try:
            admin_metrics = platform.admin_system_metrics()
        except Exception:  # noqa: BLE001
            admin_metrics = {"message": UNAVAILABLE_MESSAGE}
    return {
        "ops": ops,
        "admin_metrics": admin_metrics,
        "note": "Monitoring Center reuses Production Ops + Admin metrics — no duplicate probes.",
    }


def _backup(
    platform: Any,
    api_state: Any,
    body: dict[str, Any],
    ops_deps: Any = None,
) -> dict[str, Any]:
    if platform is None:
        return {"available": False, "message": UNAVAILABLE_MESSAGE}
    payload = {"backup_action": body.get("backup_action") or "status"}
    if body.get("snapshot_id"):
        payload["snapshot_id"] = body["snapshot_id"]
    if body.get("label"):
        payload["label"] = body["label"]
    try:
        return platform.run_production_ops(
            "backup", api_state=api_state, payload=payload, deps=ops_deps
        )
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "message": UNAVAILABLE_MESSAGE, "error": str(exc)}


def _release(
    platform: Any,
    api_state: Any,
    registry: Any,
    ops_deps: Any = None,
) -> dict[str, Any]:
    version = None
    if platform is not None:
        try:
            version = platform.run_production_ops(
                "version", api_state=api_state, deps=ops_deps
            )
        except Exception:  # noqa: BLE001
            version = {"ok": False, "message": UNAVAILABLE_MESSAGE}
    release_cfg = registry.get_module("release") or {}
    return {
        "version": version,
        "configuration": release_cfg,
        "environments": release_cfg.get("environments"),
    }


def _users_orgs(platform: Any) -> dict[str, Any]:
    users = None
    orgs = None
    if platform is not None:
        try:
            users = platform.admin_list_users()
        except Exception:  # noqa: BLE001
            users = []
        try:
            orgs = platform.run_saas_platform("list_organizations")
        except Exception:  # noqa: BLE001
            orgs = {"ok": False, "message": UNAVAILABLE_MESSAGE}
    return {
        "users": users,
        "organizations": orgs,
        "note": "Reuses Admin identity + SaaS/Enterprise organizations.",
    }


def _control_dashboard(
    platform: Any,
    api_state: Any,
    registry: Any,
    ops_deps: Any = None,
) -> dict[str, Any]:
    return {
        "modules": registry.list_modules(),
        "feature_flags": registry.get_module("feature_flags"),
        "branding": registry.get_module("branding"),
        "recent_changes": registry.history(limit=10),
        "business_rules_count": len(registry.list_rules()),
        "monitoring": _monitoring(platform, api_state, ops_deps),
        "release": _release(platform, api_state, registry, ops_deps),
        "note": "Super Admin Control Center — configuration operating system.",
    }
