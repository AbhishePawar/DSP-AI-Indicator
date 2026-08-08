"""Configuration Registry with versioning and rollback (RC1 M11)."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from threading import RLock
from typing import Any
from uuid import uuid4

from dsp_platform.control_center.defaults import MODULE_IDS, full_defaults

__all__ = [
    "ConfigurationRegistry",
    "get_configuration_registry",
    "reset_configuration_registry_for_tests",
]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


class ConfigurationRegistry:
    """Process-local durable-intent registry. Config overlays only."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._modules: dict[str, dict[str, Any]] = full_defaults()
        self._versions: list[dict[str, Any]] = []
        self._rules: list[dict[str, Any]] = []
        self._version_counter = 0
        # Seed version 0
        self._versions.append(
            {
                "version": 0,
                "module_id": "*",
                "author": "system",
                "timestamp": _now(),
                "old_value": None,
                "new_value": {"seeded": True},
                "reason": "initial registry seed",
                "approval_status": "approved",
                "change_id": "chg-seed",
            }
        )

    def list_modules(self) -> list[str]:
        return list(MODULE_IDS)

    def get_all(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return deepcopy(self._modules)

    def get_module(self, module_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._modules.get(module_id)
            return deepcopy(row) if row is not None else None

    def update_module(
        self,
        module_id: str,
        patch: dict[str, Any],
        *,
        author: str,
        reason: str | None = None,
        approval_status: str = "approved",
        replace: bool = False,
    ) -> dict[str, Any]:
        if module_id not in MODULE_IDS:
            raise ValueError(f"unknown module: {module_id}")
        with self._lock:
            old = deepcopy(self._modules.get(module_id) or {})
            if replace:
                new = deepcopy(patch)
            else:
                new = deepcopy(old)
                new.update(patch)
            self._modules[module_id] = new
            self._version_counter += 1
            version = self._version_counter
            change = {
                "version": version,
                "module_id": module_id,
                "author": author or "anonymous",
                "timestamp": _now(),
                "old_value": old,
                "new_value": deepcopy(new),
                "reason": reason or "configuration update",
                "approval_status": approval_status,
                "change_id": f"chg-{uuid4().hex[:12]}",
                "ip": None,
            }
            self._versions.append(change)
            return {
                "module_id": module_id,
                "configuration": deepcopy(new),
                "change": change,
            }

    def history(
        self, *, module_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = list(self._versions)
            if module_id:
                rows = [r for r in rows if r.get("module_id") in {module_id, "*"}]
            rows.sort(key=lambda r: int(r.get("version") or 0), reverse=True)
            return deepcopy(rows[: max(1, min(limit, 500))])

    def rollback(
        self,
        version: int,
        *,
        author: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            target = None
            for row in self._versions:
                if int(row.get("version") or -1) == int(version):
                    target = row
                    break
            if target is None:
                raise ValueError("version not found")
            module_id = str(target.get("module_id") or "")
            if module_id == "*":
                raise ValueError("cannot rollback seed version")
            old_value = target.get("old_value")
            if old_value is None:
                raise ValueError("no prior value to restore")
            current = deepcopy(self._modules.get(module_id) or {})
            self._modules[module_id] = deepcopy(old_value)
            self._version_counter += 1
            change = {
                "version": self._version_counter,
                "module_id": module_id,
                "author": author or "anonymous",
                "timestamp": _now(),
                "old_value": current,
                "new_value": deepcopy(old_value),
                "reason": reason or f"rollback to version {version}",
                "approval_status": "approved",
                "change_id": f"chg-{uuid4().hex[:12]}",
                "rollback_of": version,
            }
            self._versions.append(change)
            return {
                "module_id": module_id,
                "configuration": deepcopy(old_value),
                "change": change,
                "rolled_back_to": version,
            }

    # -- business rules -------------------------------------------------

    def list_rules(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._rules)

    def upsert_rule(self, payload: dict[str, Any], *, author: str) -> dict[str, Any]:
        with self._lock:
            rule_id = str(payload.get("rule_id") or f"rule-{uuid4().hex[:10]}")
            existing = next((r for r in self._rules if r.get("rule_id") == rule_id), None)
            old = deepcopy(existing) if existing else None
            row = {
                "rule_id": rule_id,
                "name": str(payload.get("name") or rule_id),
                "enabled": bool(payload.get("enabled", True)),
                "category": str(payload.get("category") or "general"),
                "condition": dict(payload.get("condition") or {}),
                "action": dict(payload.get("action") or {}),
                "updated_at": _now(),
                "updated_by": author,
            }
            if existing:
                self._rules = [row if r.get("rule_id") == rule_id else r for r in self._rules]
            else:
                row["created_at"] = _now()
                self._rules.append(row)
            self._version_counter += 1
            self._versions.append(
                {
                    "version": self._version_counter,
                    "module_id": "business_rules",
                    "author": author,
                    "timestamp": _now(),
                    "old_value": old,
                    "new_value": deepcopy(row),
                    "reason": payload.get("reason") or "business rule upsert",
                    "approval_status": payload.get("approval_status") or "approved",
                    "change_id": f"chg-{uuid4().hex[:12]}",
                }
            )
            return deepcopy(row)

    def delete_rule(self, rule_id: str, *, author: str) -> bool:
        with self._lock:
            before = len(self._rules)
            removed = next((r for r in self._rules if r.get("rule_id") == rule_id), None)
            self._rules = [r for r in self._rules if r.get("rule_id") != rule_id]
            if removed:
                self._version_counter += 1
                self._versions.append(
                    {
                        "version": self._version_counter,
                        "module_id": "business_rules",
                        "author": author,
                        "timestamp": _now(),
                        "old_value": removed,
                        "new_value": None,
                        "reason": "business rule delete",
                        "approval_status": "approved",
                        "change_id": f"chg-{uuid4().hex[:12]}",
                    }
                )
            return len(self._rules) < before

    def export_audit(self, *, limit: int = 200) -> list[dict[str, Any]]:
        return self.history(limit=limit)


_REGISTRY: ConfigurationRegistry | None = None


def get_configuration_registry() -> ConfigurationRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ConfigurationRegistry()
    return _REGISTRY


def reset_configuration_registry_for_tests(
    registry: ConfigurationRegistry | None = None,
) -> ConfigurationRegistry:
    global _REGISTRY
    _REGISTRY = registry if registry is not None else ConfigurationRegistry()
    return _REGISTRY
