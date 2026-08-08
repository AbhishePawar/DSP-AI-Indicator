"""Composition-root wiring for Production Ops dependencies (ASI-003).

api_platform may import dsp_platform and production_platform. dsp_platform must
not import either — inject concrete helpers here.
"""

from __future__ import annotations

from api_platform.api.monitoring import get_lifecycle_state
from api_platform.api.ops import (
    collect_component_statuses,
    collect_health_snapshot,
    get_build_metadata,
    metrics_registry,
    resolve_platform_status,
)
from dsp_platform.production_ops import ProductionOpsDeps
from production_platform.production.backup import (
    NullBackupAdapter,
    NullSecretRotationHook,
    NullVaultSecretsProvider,
)
from production_platform.production.correlation import get_correlation_id
from production_platform.production.otel_tracing import try_build_otel_tracing

__all__ = ["build_production_ops_deps"]


def build_production_ops_deps() -> ProductionOpsDeps:
    """Build injected ports for DSPPlatform.run_production_ops."""
    return ProductionOpsDeps(
        get_build_metadata=get_build_metadata,
        collect_component_statuses=collect_component_statuses,
        collect_health_snapshot=collect_health_snapshot,
        resolve_platform_status=resolve_platform_status,
        get_lifecycle_state=get_lifecycle_state,
        render_prometheus=metrics_registry.render_prometheus,
        try_build_otel_tracing=try_build_otel_tracing,
        get_correlation_id=get_correlation_id,
        backup_adapter=NullBackupAdapter(),
        secret_rotation_hook=NullSecretRotationHook(),
        vault_secrets_provider=NullVaultSecretsProvider(),
    )
