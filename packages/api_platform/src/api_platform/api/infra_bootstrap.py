"""Optional production infrastructure bootstrap (EPIC-011A).

Loaded via ``importlib`` so static architecture boundaries remain intact
(``api_platform`` must not statically import ``production_platform``).
Failures are typed and never leak DSNs/secrets into HTTP responses.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any

__all__ = [
    "InfraBootstrapResult",
    "bootstrap_production_infrastructure",
    "public_startup_error",
]


@dataclass(frozen=True, slots=True)
class InfraBootstrapResult:
    """Resolved infra handles attached to the FastAPI app."""

    infrastructure: Any | None
    production: Any | None
    notes: tuple[str, ...]
    error_code: str | None = None
    error_public: str | None = None


def public_startup_error(exc: BaseException) -> tuple[str, str]:
    """Map bootstrap failures to safe public ``(code, message)``."""
    safe = getattr(exc, "public_code", None)
    msg = getattr(exc, "public_message", None)
    if isinstance(safe, str) and isinstance(msg, str):
        return safe, msg
    try:
        mod = importlib.import_module("production_platform")
        return mod.safe_public_message(exc)  # type: ignore[no-any-return]
    except Exception:  # noqa: BLE001
        return "STARTUP_ERROR", "service failed to start"


def bootstrap_production_infrastructure(
    *,
    force_offline: bool | None = None,
) -> InfraBootstrapResult:
    """Build InfrastructureBundle + ProductionBundle from the environment.

    Development/test: always succeeds with memory adapters when vendors
    are absent. Production: raises StartupError / DependencyError subclasses
    when required dependencies are missing (caller decides process exit).
    """
    offline_flag = (
        force_offline
        if force_offline is not None
        else os.environ.get("DSP_INFRA_OFFLINE", "").lower()
        in {"1", "true", "yes", "on"}
    )
    try:
        production_platform = importlib.import_module("production_platform")
    except ImportError:
        return InfraBootstrapResult(
            infrastructure=None,
            production=None,
            notes=("production_platform not installed; infra skipped",),
            error_code="DEPENDENCY_ERROR",
            error_public="a required dependency is unavailable",
        )

    try:
        infra = production_platform.build_runtime_infrastructure(
            force_offline=offline_flag
        )
        production = production_platform.ProductionBundle.create(
            infrastructure=infra,
            with_observability=True,
        )
        notes = list(infra.diagnostics.notes) + list(getattr(infra, "notes", []) or [])
        notes.append(
            f"database={infra.diagnostics.database_adapter} "
            f"cache={infra.diagnostics.cache_adapter}"
        )
        return InfraBootstrapResult(
            infrastructure=infra,
            production=production,
            notes=tuple(notes),
        )
    except Exception as exc:  # noqa: BLE001
        code, message = public_startup_error(exc)
        # Non-production: degrade to offline rather than crash the API.
        env = (os.environ.get("DSP_ENVIRONMENT") or "development").lower()
        if env != "production" and not offline_flag:
            try:
                infra = production_platform.build_runtime_infrastructure(
                    force_offline=True
                )
                production = production_platform.ProductionBundle.create(
                    infrastructure=infra,
                    with_observability=True,
                )
                return InfraBootstrapResult(
                    infrastructure=infra,
                    production=production,
                    notes=(
                        f"degraded_offline after {code}",
                        message,
                    ),
                    error_code=code,
                    error_public=message,
                )
            except Exception:  # noqa: BLE001
                pass
        raise
