"""Runtime validation and infrastructure bootstrap (EPIC-011A).

Validates environment completeness, builds InfrastructureBundle with
Postgres/Redis adapters when available, and fails startup gracefully in
strict/production profiles without leaking secrets.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from production_platform.production.configuration import (
    Environment,
    ProductionConfiguration,
    load_configuration_from_environ,
)
from production_platform.production.exceptions import (
    ConfigurationError,
    DatabaseUnavailableError,
    RedisUnavailableError,
    StartupError,
)
from production_platform.production.infrastructure import InfrastructureBundle
from production_platform.production.versioning import resolve_application_version

__all__ = [
    "RuntimeValidationReport",
    "build_runtime_infrastructure",
    "required_env_vars",
    "validate_runtime_environment",
]


# Variables required when DSP_ENVIRONMENT=production (strict).
_PRODUCTION_REQUIRED = (
    "DSP_ENVIRONMENT",
    "DSP_REGION",
    "DSP_DATABASE_URL",
)

# Always useful; warned when missing in staging/production.
_RECOMMENDED = (
    "DSP_REDIS_URL",
    "DSP_APP_VERSION",
    "DSP_SERVICE_VERSION",
    "DSP_LOG_LEVEL",
    "GIT_SHA",
    "BUILD_TIMESTAMP",
)


@dataclass(frozen=True, slots=True)
class RuntimeValidationReport:
    """Result of env / config completeness checks — no secret values."""

    ok: bool
    environment: str
    application_version: str
    missing_required: tuple[str, ...]
    warnings: tuple[str, ...]
    notes: tuple[str, ...]

    def raise_if_invalid(self) -> None:
        if self.ok:
            return
        missing = ", ".join(self.missing_required) or "unknown"
        raise StartupError(
            f"runtime validation failed for environment={self.environment}; "
            f"missing required variables: {missing}"
        )


def required_env_vars(environment: Environment | str) -> tuple[str, ...]:
    """Return required variable names for a profile."""
    env = (
        environment
        if isinstance(environment, Environment)
        else Environment(str(environment).lower())
    )
    if env is Environment.PRODUCTION:
        return _PRODUCTION_REQUIRED
    if env is Environment.STAGING:
        return ("DSP_ENVIRONMENT",)
    return ()


def validate_runtime_environment(
    environ: Mapping[str, str] | None = None,
    *,
    strict: bool | None = None,
) -> RuntimeValidationReport:
    """Validate env completeness for the active profile.

    ``strict`` defaults to True when environment is production.
    """
    env_map = dict(environ if environ is not None else os.environ)
    profile = (
        env_map.get("DSP_ENVIRONMENT") or env_map.get("ENVIRONMENT") or "development"
    ).lower()
    notes: list[str] = []
    warnings: list[str] = []
    missing: list[str] = []

    try:
        environment = Environment(profile)
    except ValueError:
        return RuntimeValidationReport(
            ok=False,
            environment=profile,
            application_version=resolve_application_version(env_map),
            missing_required=("DSP_ENVIRONMENT",),
            warnings=(),
            notes=(f"unknown DSP_ENVIRONMENT: {profile}",),
        )

    is_strict = strict if strict is not None else environment is Environment.PRODUCTION
    required = required_env_vars(environment)

    for key in required:
        if key == "DSP_DATABASE_URL":
            if not (env_map.get("DSP_DATABASE_URL") or env_map.get("DATABASE_URL")):
                missing.append("DSP_DATABASE_URL")
            continue
        if key == "DSP_REGION":
            region = (env_map.get("DSP_REGION") or "").strip()
            if not region or region == "local":
                missing.append("DSP_REGION")
            continue
        if not (env_map.get(key) or "").strip():
            missing.append(key)

    for key in _RECOMMENDED:
        if key in {"DSP_APP_VERSION", "DSP_SERVICE_VERSION"}:
            if not (
                env_map.get("DSP_APP_VERSION") or env_map.get("DSP_SERVICE_VERSION")
            ):
                warnings.append(f"{key} unset; using VERSION file or default")
            continue
        if key == "DSP_REDIS_URL" and not (
            env_map.get("DSP_REDIS_URL") or env_map.get("REDIS_URL")
        ):
            if environment in {Environment.STAGING, Environment.PRODUCTION}:
                warnings.append(
                    "DSP_REDIS_URL unset; cache/session/rate-limit/lock use memory"
                )
            continue
        if not (env_map.get(key) or "").strip() and environment in {
            Environment.STAGING,
            Environment.PRODUCTION,
        }:
            warnings.append(f"{key} unset")

    # Typed config load — surface ConfigurationError as validation failure.
    try:
        cfg = load_configuration_from_environ(env_map)
        from production_platform.production.configuration import ConfigurationManager

        ConfigurationManager(cfg).validate()
    except ConfigurationError as exc:
        missing.append("configuration")
        notes.append(str(exc))
        cfg = None
    else:
        notes.append(f"service={cfg.service_name} version={cfg.service_version}")

    ok = not missing if is_strict else True
    if missing and not is_strict:
        notes.append(
            "non-strict profile: missing required vars recorded but not blocking"
        )
        notes.append(f"would_require={','.join(missing)}")

    return RuntimeValidationReport(
        ok=ok and (cfg is not None or not is_strict),
        environment=environment.value,
        application_version=resolve_application_version(env_map),
        missing_required=tuple(missing),
        warnings=tuple(warnings),
        notes=tuple(notes),
    )


def build_runtime_infrastructure(
    *,
    environ: Mapping[str, str] | None = None,
    force_offline: bool = False,
    strict: bool | None = None,
    require_database: bool | None = None,
    require_redis: bool | None = None,
) -> InfrastructureBundle:
    """Validate env and compose InfrastructureBundle.

    - Development/test: memory adapters by default; optional Postgres/Redis.
    - Production (strict): fails when required env missing or DB unavailable.
    - Redis: optional unless ``require_redis=True`` or graceful_fallback=false.
    """
    env_map = dict(environ if environ is not None else os.environ)
    if force_offline or _truthy(env_map.get("DSP_INFRA_OFFLINE")):
        report = validate_runtime_environment(env_map, strict=False)
        cfg = load_configuration_from_environ(env_map)
        bundle = InfrastructureBundle.create_offline(configuration=cfg)
        bundle.notes.append("force_offline=true")
        bundle.notes.extend(report.warnings)
        return bundle

    report = validate_runtime_environment(env_map, strict=strict)
    report.raise_if_invalid()

    try:
        infra = InfrastructureBundle.from_environment(environ=env_map)
    except Exception as exc:  # noqa: BLE001
        raise StartupError("infrastructure composition failed") from exc

    cfg = infra.configuration.get()
    env = cfg.environment
    need_db = (
        require_database
        if require_database is not None
        else env is Environment.PRODUCTION
    )
    need_redis = require_redis is True or (
        bool(cfg.redis.url) and not cfg.redis.graceful_fallback
    )

    db_adapter = infra.diagnostics.database_adapter
    if need_db:
        if db_adapter == "InMemoryDatabasePort" or not infra.database.ping():
            raise DatabaseUnavailableError(
                "PostgreSQL required for this profile but adapter is unavailable"
            )

    if need_redis and infra.diagnostics.redis_fallback_active:
        raise RedisUnavailableError(
            "Redis required (graceful_fallback disabled) but adapter is unavailable"
        )

    infra.notes.extend(report.warnings)
    infra.notes.append(
        f"runtime_ok environment={report.environment} "
        f"app_version={report.application_version}"
    )
    return infra


def _truthy(value: str | None) -> bool:
    if value is None or value == "":
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}
