"""Injected dependencies for Production Ops (ASI-003).

Composition roots (e.g. api_platform) supply callables/adapters. This module
never imports api_platform or production_platform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

__all__ = ["ProductionOpsDeps"]


@dataclass(frozen=True, slots=True)
class ProductionOpsDeps:
    """Optional ports for ops aggregation — all fields duck-typed callables/objects."""

    get_build_metadata: Callable[[], Any] | None = None
    collect_component_statuses: Callable[..., Any] | None = None
    collect_health_snapshot: Callable[..., Any] | None = None
    resolve_platform_status: Callable[..., Any] | None = None
    get_lifecycle_state: Callable[[], Any] | None = None
    render_prometheus: Callable[[], str] | None = None
    try_build_otel_tracing: Callable[[], Any] | None = None
    get_correlation_id: Callable[[], Any] | None = None
    backup_adapter: Any | None = None
    secret_rotation_hook: Any | None = None
    vault_secrets_provider: Any | None = None
