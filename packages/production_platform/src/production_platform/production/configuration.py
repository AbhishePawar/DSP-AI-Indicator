"""Configuration and secrets — provider-neutral managers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from threading import Lock

from production_platform.production.exceptions import ConfigurationError
from production_platform.production.interfaces import SecretsPort

__all__ = [
    "ConfigurationManager",
    "Environment",
    "InMemorySecretsPort",
    "ProductionConfiguration",
]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True, slots=True)
class ProductionConfiguration:
    """Immutable production configuration snapshot."""

    environment: Environment = Environment.DEVELOPMENT
    service_name: str = "dsp-ai-indicator"
    service_version: str = "0.1.0"
    region: str = "local"
    log_level: str = "INFO"
    metrics_enabled: bool = True
    tracing_enabled: bool = True
    cache_default_ttl_seconds: float = 300.0
    settings: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.service_name.strip():
            msg = "service_name must not be empty"
            raise ConfigurationError(msg)
        if not self.service_version.strip():
            msg = "service_version must not be empty"
            raise ConfigurationError(msg)
        if self.cache_default_ttl_seconds < 0:
            msg = "cache_default_ttl_seconds must be non-negative"
            raise ConfigurationError(msg)
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

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        return self._configuration.settings.get(key, default)

    def get_secret(self, name: str) -> str | None:
        return self._secrets.get_secret(name)

    def validate(self) -> None:
        """Re-validate configuration consistency."""
        _ = ProductionConfiguration(
            environment=self._configuration.environment,
            service_name=self._configuration.service_name,
            service_version=self._configuration.service_version,
            region=self._configuration.region,
            log_level=self._configuration.log_level,
            metrics_enabled=self._configuration.metrics_enabled,
            tracing_enabled=self._configuration.tracing_enabled,
            cache_default_ttl_seconds=self._configuration.cache_default_ttl_seconds,
            settings=self._configuration.settings,
        )
