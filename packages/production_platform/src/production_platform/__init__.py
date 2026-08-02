"""DSP Production Services — provider-neutral ops layer (K1.3 + PEP-002 + PEP-003).

Independent of business logic, HTTP routing, and authentication.
Vendor adapters are optional and loaded lazily at the composition root only.
"""

from __future__ import annotations

from production_platform.production.audit_events import (
    AuditEvent,
    FanoutAuditEventPort,
    InMemoryAuditEventPort,
    LoggingAuditEventPort,
)
from production_platform.production.background import InMemoryBackgroundTaskPort
from production_platform.production.bundle import ProductionBundle
from production_platform.production.cache import (
    FallbackCachePort,
    InMemoryCachePort,
    PatternCacheInvalidation,
)
from production_platform.production.clock import FixedClockPort, SystemClockPort
from production_platform.production.configuration import (
    ConfigurationManager,
    DatabaseSettings,
    Environment,
    EnvSecretsPort,
    IndiaSettings,
    InMemorySecretsPort,
    JobQueueSettings,
    ObjectStorageSettings,
    ProductionConfiguration,
    RedisSettings,
    load_configuration_from_environ,
)
from production_platform.production.correlation import (
    correlation_context,
    get_correlation_id,
    new_request_id,
)
from production_platform.production.database import InMemoryDatabasePort, SqlRepository
from production_platform.production.diagnostics import (
    DiagnosticsManager,
    DiagnosticsReport,
    ProductionMetadata,
)
from production_platform.production.exceptions import (
    ConfigurationError,
    DatabaseUnavailableError,
    DependencyError,
    ProductionError,
    ProviderError,
    RedisUnavailableError,
    StartupError,
    safe_public_message,
)
from production_platform.production.runtime import (
    RuntimeValidationReport,
    build_runtime_infrastructure,
    required_env_vars,
    validate_runtime_environment,
)
from production_platform.production.versioning import (
    normalize_version,
    resolve_application_version,
    resolve_service_version,
)
from production_platform.production.feature_flags import (
    FeatureFlag,
    FeatureFlagManager,
)
from production_platform.production.health import (
    HealthCheckResult,
    HealthManager,
    HealthReport,
    HealthStatus,
)
from production_platform.production.india import (
    IndiaOperationalProfile,
    StaticIndiaMarketCalendar,
    build_india_profile,
)
from production_platform.production.infrastructure import (
    InfrastructureBundle,
    InfrastructureDiagnostics,
)
from production_platform.production.interfaces import (
    AuditEventPort,
    BackgroundTaskPort,
    CacheInvalidationPort,
    CachePort,
    ClockPort,
    ConfigurationPort,
    DatabasePort,
    HealthPort,
    JobQueuePort,
    LockPort,
    LoggingPort,
    MarketCalendarPort,
    MetricsPort,
    QueuePort,
    RateLimiterPort,
    RateLimitPort,
    Repository,
    RepositoryFactoryPort,
    SchedulerPort,
    SecretProviderPort,
    SecretsPort,
    SessionPort,
    StoragePort,
    TracingPort,
    TransactionPort,
)
from production_platform.production.job_queue import InMemoryJobQueuePort, RetryPolicy
from production_platform.production.json_logging import (
    FanoutLoggingPort,
    JsonLoggingPort,
    ObservabilityLogEvent,
)
from production_platform.production.locking import InMemoryLockPort
from production_platform.production.logging import (
    InMemoryLoggingPort,
    LogRecord,
    StdlibLoggingPort,
    new_correlation_id,
)
from production_platform.production.metrics import InMemoryMetricsPort, MetricSample
from production_platform.production.migrations import Migration, MigrationRunner
from production_platform.production.observability import (
    ObservabilityBundle,
    ObservabilitySettings,
)
from production_platform.production.otel_tracing import (
    OpenTelemetryTracingPort,
    try_build_otel_tracing,
)
from production_platform.production.prometheus_metrics import (
    PrometheusTextRenderer,
    render_prometheus,
    try_build_prometheus_client_metrics,
)
from production_platform.production.rate_limit import InMemoryRateLimitPort
from production_platform.production.repository import DefaultRepositoryFactory
from production_platform.production.scheduler import (
    InMemorySchedulerPort,
    ScheduledJob,
)
from production_platform.production.session import InMemorySessionPort
from production_platform.production.storage import (
    InMemoryStoragePort,
    LocalFilesystemStoragePort,
    StoredObject,
)
from production_platform.production.tracing import InMemoryTracingPort, SpanRecord

__all__ = [
    "AuditEvent",
    "AuditEventPort",
    "BackgroundTaskPort",
    "CacheInvalidationPort",
    "CachePort",
    "ClockPort",
    "ConfigurationError",
    "ConfigurationManager",
    "ConfigurationPort",
    "DatabasePort",
    "DatabaseSettings",
    "DatabaseUnavailableError",
    "DefaultRepositoryFactory",
    "DependencyError",
    "DiagnosticsManager",
    "DiagnosticsReport",
    "Environment",
    "EnvSecretsPort",
    "FallbackCachePort",
    "FanoutAuditEventPort",
    "FanoutLoggingPort",
    "FeatureFlag",
    "FeatureFlagManager",
    "FixedClockPort",
    "HealthCheckResult",
    "HealthManager",
    "HealthPort",
    "HealthReport",
    "HealthStatus",
    "IndiaOperationalProfile",
    "IndiaSettings",
    "InMemoryAuditEventPort",
    "InMemoryBackgroundTaskPort",
    "InMemoryCachePort",
    "InMemoryDatabasePort",
    "InMemoryJobQueuePort",
    "InMemoryLockPort",
    "InMemoryLoggingPort",
    "InMemoryMetricsPort",
    "InMemoryRateLimitPort",
    "InMemorySchedulerPort",
    "InMemorySecretsPort",
    "InMemorySessionPort",
    "InMemoryStoragePort",
    "InMemoryTracingPort",
    "InfrastructureBundle",
    "InfrastructureDiagnostics",
    "JobQueuePort",
    "JobQueueSettings",
    "JsonLoggingPort",
    "LocalFilesystemStoragePort",
    "LockPort",
    "LogRecord",
    "LoggingAuditEventPort",
    "LoggingPort",
    "MarketCalendarPort",
    "MetricSample",
    "MetricsPort",
    "Migration",
    "MigrationRunner",
    "ObjectStorageSettings",
    "ObservabilityBundle",
    "ObservabilityLogEvent",
    "ObservabilitySettings",
    "OpenTelemetryTracingPort",
    "PatternCacheInvalidation",
    "ProductionBundle",
    "ProductionConfiguration",
    "ProductionError",
    "ProductionMetadata",
    "PrometheusTextRenderer",
    "ProviderError",
    "QueuePort",
    "RateLimitPort",
    "RateLimiterPort",
    "RedisSettings",
    "RedisUnavailableError",
    "Repository",
    "RepositoryFactoryPort",
    "RetryPolicy",
    "RuntimeValidationReport",
    "ScheduledJob",
    "SchedulerPort",
    "SecretProviderPort",
    "SecretsPort",
    "SessionPort",
    "SpanRecord",
    "SqlRepository",
    "StartupError",
    "StaticIndiaMarketCalendar",
    "StdlibLoggingPort",
    "StoragePort",
    "StoredObject",
    "SystemClockPort",
    "TracingPort",
    "TransactionPort",
    "build_india_profile",
    "build_runtime_infrastructure",
    "correlation_context",
    "get_correlation_id",
    "load_configuration_from_environ",
    "new_correlation_id",
    "new_request_id",
    "normalize_version",
    "render_prometheus",
    "required_env_vars",
    "resolve_application_version",
    "resolve_service_version",
    "safe_public_message",
    "try_build_otel_tracing",
    "try_build_prometheus_client_metrics",
    "validate_runtime_environment",
    "__version__",
]

__version__ = "0.3.0"
