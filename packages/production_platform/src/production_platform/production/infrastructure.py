"""Infrastructure composition root (PEP-002 Phase 4).

ONLY this module (and ProductionBundle) may select vendor adapters.
Business packages receive ports — never Postgres/Redis/S3 clients.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from production_platform.production.background import (
    InMemoryBackgroundTaskPort,
    ensure_background_task_port,
)
from production_platform.production.cache import (
    FallbackCachePort,
    InMemoryCachePort,
    PatternCacheInvalidation,
    ensure_cache_port,
)
from production_platform.production.clock import ensure_clock_port
from production_platform.production.configuration import (
    ConfigurationManager,
    Environment,
    EnvSecretsPort,
    InMemorySecretsPort,
    ProductionConfiguration,
    load_configuration_from_environ,
)
from production_platform.production.database import (
    InMemoryDatabasePort,
    ensure_database_port,
)
from production_platform.production.exceptions import ConfigurationError, ProviderError
from production_platform.production.india import (
    IndiaOperationalProfile,
    build_india_profile,
)
from production_platform.production.interfaces import (
    BackgroundTaskPort,
    CachePort,
    ClockPort,
    DatabasePort,
    JobQueuePort,
    LockPort,
    RateLimitPort,
    RepositoryFactoryPort,
    SecretsPort,
    SessionPort,
    StoragePort,
)
from production_platform.production.job_queue import (
    InMemoryJobQueuePort,
    RetryPolicy,
    ensure_job_queue_port,
)
from production_platform.production.locking import InMemoryLockPort, ensure_lock_port
from production_platform.production.rate_limit import (
    InMemoryRateLimitPort,
    ensure_rate_limit_port,
)
from production_platform.production.repository import ensure_repository_factory
from production_platform.production.session import (
    InMemorySessionPort,
    ensure_session_port,
)
from production_platform.production.storage import (
    InMemoryStoragePort,
    LocalFilesystemStoragePort,
    ensure_storage_port,
)

__all__ = ["InfrastructureBundle", "InfrastructureDiagnostics"]


@dataclass(frozen=True, slots=True)
class InfrastructureDiagnostics:
    """Honest adapter selection report — no secrets."""

    database_adapter: str
    cache_adapter: str
    rate_limit_adapter: str
    lock_adapter: str
    session_adapter: str
    storage_adapter: str
    job_queue_adapter: str
    secrets_adapter: str
    redis_fallback_active: bool
    notes: tuple[str, ...] = ()


@dataclass
class InfrastructureBundle:
    """Resolved infrastructure ports for one process."""

    configuration: ConfigurationManager
    database: DatabasePort
    repositories: RepositoryFactoryPort
    cache: CachePort
    rate_limit: RateLimitPort
    lock: LockPort
    session: SessionPort
    storage: StoragePort
    job_queue: JobQueuePort
    background_tasks: BackgroundTaskPort
    secrets: SecretsPort
    clock: ClockPort
    india: IndiaOperationalProfile
    cache_invalidation: PatternCacheInvalidation
    diagnostics: InfrastructureDiagnostics
    notes: list[str] = field(default_factory=list)

    @classmethod
    def create_offline(
        cls,
        *,
        configuration: ProductionConfiguration | None = None,
        secrets: SecretsPort | None = None,
    ) -> InfrastructureBundle:
        """Deterministic in-memory stack — CI / local / engine tests."""
        cfg = configuration or ProductionConfiguration()
        secrets_port = secrets if secrets is not None else InMemorySecretsPort()
        config_mgr = ConfigurationManager(cfg, secrets=secrets_port)
        database = InMemoryDatabasePort()
        cache = InMemoryCachePort()
        queue = InMemoryJobQueuePort(
            retry_policy=RetryPolicy(max_attempts=cfg.job_queue.max_attempts)
        )
        diag = InfrastructureDiagnostics(
            database_adapter=type(database).__name__,
            cache_adapter=type(cache).__name__,
            rate_limit_adapter="InMemoryRateLimitPort",
            lock_adapter="InMemoryLockPort",
            session_adapter="InMemorySessionPort",
            storage_adapter="InMemoryStoragePort",
            job_queue_adapter=type(queue).__name__,
            secrets_adapter=type(secrets_port).__name__,
            redis_fallback_active=False,
            notes=("offline reference adapters",),
        )
        return cls(
            configuration=config_mgr,
            database=database,
            repositories=ensure_repository_factory(None, database=database),
            cache=cache,
            rate_limit=InMemoryRateLimitPort(),
            lock=InMemoryLockPort(),
            session=InMemorySessionPort(),
            storage=InMemoryStoragePort(),
            job_queue=queue,
            background_tasks=InMemoryBackgroundTaskPort(queue),
            secrets=secrets_port,
            clock=ensure_clock_port(None),
            india=build_india_profile(cfg.india),
            cache_invalidation=PatternCacheInvalidation(cache),
            diagnostics=diag,
            notes=list(diag.notes),
        )

    @classmethod
    def from_environment(
        cls,
        *,
        environ: dict[str, str] | None = None,
        force_offline: bool = False,
    ) -> InfrastructureBundle:
        """Composition root: resolve optional vendors with graceful fallback."""
        if force_offline:
            cfg = (
                load_configuration_from_environ(environ)
                if environ is not None
                else ProductionConfiguration()
            )
            return cls.create_offline(configuration=cfg)

        cfg = load_configuration_from_environ(environ)
        secrets: SecretsPort = EnvSecretsPort(environ=environ) if environ is not None else EnvSecretsPort()
        notes: list[str] = []

        database = ensure_database_port(None)
        db_name = type(database).__name__
        if cfg.database.url:
            from production_platform.adapters.postgres import build_postgres

            try:
                pg = build_postgres(
                    cfg.database.url,
                    connect_timeout=cfg.database.connect_timeout_seconds,
                    application_name=cfg.database.application_name,
                )
            except (ConfigurationError, ProviderError, ImportError) as exc:
                # Production must never silently degrade to InMemoryDatabasePort;
                # the real reason has to reach startup logs.
                if cfg.environment is Environment.PRODUCTION:
                    raise
                notes.append(
                    f"PostgreSQL unavailable or driver missing ({exc}); "
                    "using InMemoryDatabasePort"
                )
            else:
                database = pg
                db_name = type(pg).__name__

        cache: CachePort = InMemoryCachePort()
        rate_limit: RateLimitPort = InMemoryRateLimitPort()
        lock: LockPort = InMemoryLockPort()
        session: SessionPort = InMemorySessionPort()
        redis_fallback = False

        if cfg.redis.url:
            from production_platform.adapters.redis_stack import try_build_redis_stack

            stack = try_build_redis_stack(
                cfg.redis.url,
                key_prefix=cfg.redis.key_prefix,
                socket_timeout=cfg.redis.connect_timeout_seconds,
            )
            if stack is not None:
                # Prefer Redis; wrap with memory fallback for mid-flight outages.
                memory = InMemoryCachePort()
                cache = (
                    FallbackCachePort(stack["cache"], memory)
                    if cfg.redis.graceful_fallback
                    else stack["cache"]
                )
                rate_limit = stack["rate_limit"]
                lock = stack["lock"]
                session = stack["session"]
            elif cfg.redis.graceful_fallback:
                redis_fallback = True
                notes.append(
                    "Redis unavailable or driver missing; cache/rate/lock/session degraded to memory"
                )
            else:
                notes.append("Redis unavailable and graceful_fallback=false")

        storage: StoragePort = InMemoryStoragePort()
        provider = cfg.object_storage.provider
        if provider == "local" and cfg.object_storage.local_root:
            storage = LocalFilesystemStoragePort(cfg.object_storage.local_root)
        elif provider in {"s3", "minio"}:
            from production_platform.adapters.object_storage import try_build_s3_storage

            s3 = try_build_s3_storage(
                bucket=cfg.object_storage.bucket,
                endpoint_url=cfg.object_storage.endpoint_url,
                region=cfg.object_storage.region,
            )
            if s3 is not None:
                storage = s3
            else:
                notes.append(
                    f"Object storage provider={provider} unavailable; using InMemoryStoragePort"
                )

        queue = InMemoryJobQueuePort(
            retry_policy=RetryPolicy(
                max_attempts=cfg.job_queue.max_attempts,
                base_delay_seconds=cfg.job_queue.base_delay_seconds,
            )
        )
        if cfg.job_queue.backend != "memory":
            notes.append(
                f"job_queue.backend={cfg.job_queue.backend} reserved; using InMemoryJobQueuePort until worker epic"
            )

        config_mgr = ConfigurationManager(cfg, secrets=secrets)
        diag = InfrastructureDiagnostics(
            database_adapter=db_name,
            cache_adapter=type(cache).__name__,
            rate_limit_adapter=type(rate_limit).__name__,
            lock_adapter=type(lock).__name__,
            session_adapter=type(session).__name__,
            storage_adapter=type(storage).__name__,
            job_queue_adapter=type(queue).__name__,
            secrets_adapter=type(secrets).__name__,
            redis_fallback_active=redis_fallback,
            notes=tuple(notes),
        )
        return cls(
            configuration=config_mgr,
            database=database,
            repositories=ensure_repository_factory(None, database=database),
            cache=ensure_cache_port(cache),
            rate_limit=ensure_rate_limit_port(rate_limit),
            lock=ensure_lock_port(lock),
            session=ensure_session_port(session),
            storage=ensure_storage_port(storage),
            job_queue=ensure_job_queue_port(queue),
            background_tasks=ensure_background_task_port(
                InMemoryBackgroundTaskPort(queue)
            ),
            secrets=secrets,
            clock=ensure_clock_port(None),
            india=build_india_profile(cfg.india),
            cache_invalidation=PatternCacheInvalidation(cache),
            diagnostics=diag,
            notes=notes,
        )

    def health_checks(self) -> dict[str, Any]:
        """Lightweight infra probes for readiness aggregation."""
        redis_configured = bool(self.configuration.get().redis.url)
        redis_status = "skip"
        if redis_configured:
            if self.diagnostics.redis_fallback_active:
                redis_status = "degraded"
            elif "Redis" in self.diagnostics.cache_adapter or "Fallback" in (
                self.diagnostics.cache_adapter
            ):
                redis_status = "pass"
            else:
                redis_status = "fail"
        return {
            "database": self.database.ping(),
            "database_adapter": self.diagnostics.database_adapter,
            "cache_adapter": type(self.cache).__name__,
            "redis": {
                "configured": redis_configured,
                "status": redis_status,
                "fallback_active": self.diagnostics.redis_fallback_active,
                "rate_limit_adapter": self.diagnostics.rate_limit_adapter,
                "lock_adapter": self.diagnostics.lock_adapter,
                "session_adapter": self.diagnostics.session_adapter,
            },
            "storage_adapter": type(self.storage).__name__,
            "india_timezone": self.india.timezone,
            "india_currency": self.india.currency,
            "diagnostics": {
                "database": self.diagnostics.database_adapter,
                "cache": self.diagnostics.cache_adapter,
                "redis_fallback": self.diagnostics.redis_fallback_active,
                "notes": list(self.diagnostics.notes),
            },
        }

