"""DSP Production Services — provider-neutral ops layer (K1.3).

Independent of business logic, HTTP routing, and authentication.
Vendor adapters (Redis, Prometheus, OTel, S3, Celery, …) are external.
"""

from __future__ import annotations

from production_platform.production.bundle import ProductionBundle
from production_platform.production.cache import InMemoryCachePort
from production_platform.production.configuration import (
    ConfigurationManager,
    Environment,
    InMemorySecretsPort,
    ProductionConfiguration,
)
from production_platform.production.diagnostics import (
    DiagnosticsManager,
    DiagnosticsReport,
    ProductionMetadata,
)
from production_platform.production.exceptions import (
    ConfigurationError,
    ProductionError,
    ProviderError,
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
from production_platform.production.interfaces import (
    CachePort,
    LoggingPort,
    MetricsPort,
    SchedulerPort,
    SecretsPort,
    StoragePort,
    TracingPort,
)
from production_platform.production.logging import (
    InMemoryLoggingPort,
    LogRecord,
    StdlibLoggingPort,
    new_correlation_id,
)
from production_platform.production.metrics import InMemoryMetricsPort, MetricSample
from production_platform.production.scheduler import (
    InMemorySchedulerPort,
    ScheduledJob,
)
from production_platform.production.storage import InMemoryStoragePort, StoredObject
from production_platform.production.tracing import InMemoryTracingPort, SpanRecord

__all__ = [
    "CachePort",
    "ConfigurationError",
    "ConfigurationManager",
    "DiagnosticsManager",
    "DiagnosticsReport",
    "Environment",
    "FeatureFlag",
    "FeatureFlagManager",
    "HealthCheckResult",
    "HealthManager",
    "HealthReport",
    "HealthStatus",
    "InMemoryCachePort",
    "InMemoryLoggingPort",
    "InMemoryMetricsPort",
    "InMemorySchedulerPort",
    "InMemorySecretsPort",
    "InMemoryStoragePort",
    "InMemoryTracingPort",
    "LogRecord",
    "LoggingPort",
    "MetricSample",
    "MetricsPort",
    "ProductionBundle",
    "ProductionConfiguration",
    "ProductionError",
    "ProductionMetadata",
    "ProviderError",
    "ScheduledJob",
    "SchedulerPort",
    "SecretsPort",
    "SpanRecord",
    "StdlibLoggingPort",
    "StoragePort",
    "StoredObject",
    "TracingPort",
    "new_correlation_id",
    "__version__",
]

__version__ = "0.1.0"
