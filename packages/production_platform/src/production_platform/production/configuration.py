"""Configuration and secrets — typed profiles (K1.3 + PEP-002)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock
from typing import Mapping

from production_platform.production.exceptions import ConfigurationError
from production_platform.production.interfaces import SecretsPort

__all__ = [
    "ConfigurationManager",
    "DatabaseSettings",
    "Environment",
    "EnvSecretsPort",
    "IndiaSettings",
    "InMemorySecretsPort",
    "JobQueueSettings",
    "ObjectStorageSettings",
    "ProductionConfiguration",
    "RedisSettings",
    "load_configuration_from_environ",
]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class DatabaseSettings:
    """Relational database settings — provider-neutral URL."""

    url: str | None = None
    pool_size: int = 5
    connect_timeout_seconds: float = 5.0
    application_name: str = "dsp-ai-indicator"

    def __post_init__(self) -> None:
        if self.pool_size < 1:
            raise ConfigurationError("database.pool_size must be >= 1")
        if self.connect_timeout_seconds < 0:
            raise ConfigurationError("database.connect_timeout_seconds must be non-negative")


@dataclass(frozen=True, slots=True)
class RedisSettings:
    """Redis settings — cache / rate / lock / session."""

    url: str | None = None
    key_prefix: str = "dsp"
    connect_timeout_seconds: float = 2.0
    graceful_fallback: bool = True

    def __post_init__(self) -> None:
        if self.connect_timeout_seconds < 0:
            raise ConfigurationError("redis.connect_timeout_seconds must be non-negative")


@dataclass(frozen=True, slots=True)
class ObjectStorageSettings:
    """Object storage settings — no provider lock-in."""

    provider: str = "memory"  # memory | local | s3 | minio | azure | gcs
    bucket: str | None = None
    endpoint_url: str | None = None
    region: str | None = None
    local_root: str | None = None

    def __post_init__(self) -> None:
        allowed = {"memory", "local", "s3", "minio", "azure", "gcs"}
        if self.provider not in allowed:
            raise ConfigurationError(
                f"object_storage.provider must be one of {sorted(allowed)}"
            )


@dataclass(frozen=True, slots=True)
class JobQueueSettings:
    """Background execution settings (architecture + in-process default)."""

    backend: str = "memory"  # memory | redis_streams | sqs | rabbitmq
    max_attempts: int = 3
    base_delay_seconds: float = 1.0

    def __post_init__(self) -> None:
        allowed = {"memory", "redis_streams", "sqs", "rabbitmq"}
        if self.backend not in allowed:
            raise ConfigurationError(
                f"job_queue.backend must be one of {sorted(allowed)}"
            )
        if self.max_attempts < 1:
            raise ConfigurationError("job_queue.max_attempts must be >= 1")


@dataclass(frozen=True, slots=True)
class IndiaSettings:
    """India-first operational defaults (ADR-PEP-0010 / 0011) — architecture."""

    timezone: str = "Asia/Kolkata"
    currency: str = "INR"
    data_residency_region: str = "in"
    primary_exchanges: tuple[str, ...] = ("NSE", "BSE")
    cert_in_log_retention_days: int = 180
    dpdp_residency_required: bool = True
    enable_market_calendar: bool = True
    future_ports: tuple[str, ...] = (
        "DigiLockerPort",
        "PanVerificationPort",
        "UpiPort",
        "DematPort",
        "AccountAggregatorPort",
        "OcenPort",
    )

    def __post_init__(self) -> None:
        if self.timezone != "Asia/Kolkata" and self.data_residency_region == "in":
            # Allow override but keep honesty in validation notes via settings.
            pass
        if self.currency != "INR" and self.data_residency_region == "in":
            pass
        if self.cert_in_log_retention_days < 180:
            raise ConfigurationError(
                "india.cert_in_log_retention_days must be >= 180 (CERT-In posture)"
            )
        object.__setattr__(self, "primary_exchanges", tuple(self.primary_exchanges))
        object.__setattr__(self, "future_ports", tuple(self.future_ports))


@dataclass(frozen=True, slots=True)
class ProductionConfiguration:
    """Immutable production configuration snapshot."""

    environment: Environment = Environment.DEVELOPMENT
    service_name: str = "dsp-ai-indicator"
    service_version: str = "0.2.0"
    region: str = "local"
    log_level: str = "INFO"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    cache_default_ttl_seconds: float = 300.0
    settings: dict[str, str] = field(default_factory=dict)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    redis: RedisSettings = field(default_factory=RedisSettings)
    object_storage: ObjectStorageSettings = field(default_factory=ObjectStorageSettings)
    job_queue: JobQueueSettings = field(default_factory=JobQueueSettings)
    india: IndiaSettings = field(default_factory=IndiaSettings)

    def __post_init__(self) -> None:
        if not self.service_name.strip():
            raise ConfigurationError("service_name must not be empty")
        if not self.service_version.strip():
            raise ConfigurationError("service_version must not be empty")
        if self.cache_default_ttl_seconds < 0:
            raise ConfigurationError("cache_default_ttl_seconds must be non-negative")
        object.__setattr__(self, "settings", dict(self.settings))


class InMemorySecretsPort:
    """Process-local secrets map — never a vault SDK."""

    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self._secrets: dict[str, str] = dict(initial or {})
        self._lock = Lock()

    def get_secret(self, name: str) -> str | None:
        with self._lock:
            return self._secrets.get(name)

    def set_secret(self, name: str, value: str) -> None:
        with self._lock:
            self._secrets[name] = value

    def __repr__(self) -> str:
        with self._lock:
            keys = sorted(self._secrets)
        return f"InMemorySecretsPort(keys={keys!r})"


class EnvSecretsPort:
    """Environment-variable secrets adapter.

    Future secret managers (AWS / Azure / Vault) implement SecretsPort the same way.
    Never logs secret values.
    """

    def __init__(
        self,
        *,
        prefix: str = "DSP_SECRET_",
        environ: Mapping[str, str] | None = None,
        aliases: Mapping[str, str] | None = None,
    ) -> None:
        self._prefix = prefix
        self._environ = environ if environ is not None else os.environ
        self._aliases = dict(aliases or {})

    def get_secret(self, name: str) -> str | None:
        env_name = self._aliases.get(name, f"{self._prefix}{name.upper()}")
        value = self._environ.get(env_name)
        if value is None or value == "":
            return None
        return value

    def __repr__(self) -> str:
        return f"EnvSecretsPort(prefix={self._prefix!r})"


class ConfigurationManager:
    """Holds immutable configuration + secrets port."""

    def __init__(
        self,
        configuration: ProductionConfiguration | None = None,
        *,
        secrets: SecretsPort | None = None,
    ) -> None:
        self._configuration = configuration or ProductionConfiguration()
        self._secrets = secrets if secrets is not None else InMemorySecretsPort()

    @property
    def configuration(self) -> ProductionConfiguration:
        return self._configuration

    @property
    def secrets(self) -> SecretsPort:
        return self._secrets

    def get(self) -> ProductionConfiguration:
        return self._configuration

    def get_environment(self) -> str:
        """ConfigurationPort: environment profile name."""
        return self._configuration.environment.value

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        return self._configuration.settings.get(key, default)

    def get_secret(self, name: str) -> str | None:
        return self._secrets.get_secret(name)

    def validate(self) -> None:
        """Re-validate configuration consistency."""
        cfg = self._configuration
        _ = ProductionConfiguration(
            environment=cfg.environment,
            service_name=cfg.service_name,
            service_version=cfg.service_version,
            region=cfg.region,
            log_level=cfg.log_level,
            metrics_enabled=cfg.metrics_enabled,
            tracing_enabled=cfg.tracing_enabled,
            cache_default_ttl_seconds=cfg.cache_default_ttl_seconds,
            settings=cfg.settings,
            database=cfg.database,
            redis=cfg.redis,
            object_storage=cfg.object_storage,
            job_queue=cfg.job_queue,
            india=cfg.india,
        )
        if cfg.environment is Environment.PRODUCTION:
            if cfg.region in {"", "local"}:
                raise ConfigurationError(
                    "production environment requires a non-local region"
                )


def load_configuration_from_environ(
    environ: Mapping[str, str] | None = None,
) -> ProductionConfiguration:
    """Load typed configuration from environment variables."""
    env = environ if environ is not None else os.environ
    profile = (env.get("DSP_ENVIRONMENT") or env.get("ENVIRONMENT") or "development").lower()
    try:
        environment = Environment(profile)
    except ValueError as exc:
        raise ConfigurationError(f"unknown DSP_ENVIRONMENT: {profile}") from exc

    storage_provider = (env.get("DSP_OBJECT_STORAGE_PROVIDER") or "memory").lower()
    job_backend = (env.get("DSP_JOB_QUEUE_BACKEND") or "memory").lower()

    return ProductionConfiguration(
        environment=environment,
        service_name=env.get("DSP_SERVICE_NAME", "dsp-ai-indicator"),
        service_version=env.get("DSP_SERVICE_VERSION", "0.2.0"),
        region=env.get("DSP_REGION", "local" if environment is not Environment.PRODUCTION else "ap-south-1"),
        log_level=env.get("DSP_LOG_LEVEL", "INFO"),
        metrics_enabled=_bool(env.get("DSP_METRICS_ENABLED"), default=True),
        tracing_enabled=_bool(env.get("DSP_TRACING_ENABLED"), default=True),
        cache_default_ttl_seconds=float(env.get("DSP_CACHE_TTL_SECONDS", "300")),
        settings={k[4:].lower(): v for k, v in env.items() if k.startswith("DSP_SETTING_")},
        database=DatabaseSettings(
            url=env.get("DSP_DATABASE_URL") or env.get("DATABASE_URL"),
            pool_size=int(env.get("DSP_DATABASE_POOL_SIZE", "5")),
            connect_timeout_seconds=float(env.get("DSP_DATABASE_TIMEOUT", "5")),
            application_name=env.get("DSP_DATABASE_APP_NAME", "dsp-ai-indicator"),
        ),
        redis=RedisSettings(
            url=env.get("DSP_REDIS_URL") or env.get("REDIS_URL"),
            key_prefix=env.get("DSP_REDIS_PREFIX", "dsp"),
            connect_timeout_seconds=float(env.get("DSP_REDIS_TIMEOUT", "2")),
            graceful_fallback=_bool(env.get("DSP_REDIS_FALLBACK"), default=True),
        ),
        object_storage=ObjectStorageSettings(
            provider=storage_provider,
            bucket=env.get("DSP_OBJECT_STORAGE_BUCKET"),
            endpoint_url=env.get("DSP_OBJECT_STORAGE_ENDPOINT"),
            region=env.get("DSP_OBJECT_STORAGE_REGION"),
            local_root=env.get("DSP_OBJECT_STORAGE_LOCAL_ROOT"),
        ),
        job_queue=JobQueueSettings(
            backend=job_backend,
            max_attempts=int(env.get("DSP_JOB_MAX_ATTEMPTS", "3")),
            base_delay_seconds=float(env.get("DSP_JOB_BASE_DELAY", "1")),
        ),
        india=IndiaSettings(
            timezone=env.get("DSP_INDIA_TIMEZONE", "Asia/Kolkata"),
            currency=env.get("DSP_INDIA_CURRENCY", "INR"),
            data_residency_region=env.get("DSP_INDIA_DATA_RESIDENCY", "in"),
            cert_in_log_retention_days=int(env.get("DSP_CERT_IN_LOG_RETENTION_DAYS", "180")),
            dpdp_residency_required=_bool(env.get("DSP_DPDP_RESIDENCY"), default=True),
            enable_market_calendar=_bool(env.get("DSP_MARKET_CALENDAR"), default=True),
        ),
    )


def _bool(value: str | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
