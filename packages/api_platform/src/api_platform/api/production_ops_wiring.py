"""Composition-root wiring for Production Ops dependencies (ASI-003).

api_platform may import dsp_platform. production_platform is loaded via
importlib (same pattern as infra_bootstrap) so static architecture boundaries
stay intact. dsp_platform must not import either package.
"""

from __future__ import annotations

import importlib
from typing import Any

from api_platform.api.monitoring import get_lifecycle_state
from api_platform.api.ops import (
    collect_component_statuses,
    collect_health_snapshot,
    get_build_metadata,
    metrics_registry,
    resolve_platform_status,
)
from dsp_platform.production_ops import ProductionOpsDeps

__all__ = ["build_production_ops_deps"]


def _load_production_ops_ports() -> dict[str, Any]:
    """Resolve optional production_platform ports without a static import."""
    ports: dict[str, Any] = {
        "try_build_otel_tracing": None,
        "get_correlation_id": None,
        "backup_adapter": None,
        "secret_rotation_hook": None,
        "vault_secrets_provider": None,
    }
    try:
        otel = importlib.import_module("production_platform.production.otel_tracing")
        ports["try_build_otel_tracing"] = otel.try_build_otel_tracing
    except Exception:  # noqa: BLE001
        pass
    try:
        correlation = importlib.import_module(
            "production_platform.production.correlation"
        )
        ports["get_correlation_id"] = correlation.get_correlation_id
    except Exception:  # noqa: BLE001
        pass
    try:
        backup = importlib.import_module("production_platform.production.backup")
        ports["backup_adapter"] = backup.NullBackupAdapter()
        ports["secret_rotation_hook"] = backup.NullSecretRotationHook()
        ports["vault_secrets_provider"] = backup.NullVaultSecretsProvider()
    except Exception:  # noqa: BLE001
        pass
    return ports


def build_production_ops_deps() -> ProductionOpsDeps:
    """Build injected ports for DSPPlatform.run_production_ops."""
    ports = _load_production_ops_ports()
    return ProductionOpsDeps(
        get_build_metadata=get_build_metadata,
        collect_component_statuses=collect_component_statuses,
        collect_health_snapshot=collect_health_snapshot,
        resolve_platform_status=resolve_platform_status,
        get_lifecycle_state=get_lifecycle_state,
        render_prometheus=metrics_registry.render_prometheus,
        try_build_otel_tracing=ports["try_build_otel_tracing"],
        get_correlation_id=ports["get_correlation_id"],
        backup_adapter=ports["backup_adapter"],
        secret_rotation_hook=ports["secret_rotation_hook"],
        vault_secrets_provider=ports["vault_secrets_provider"],
    )
