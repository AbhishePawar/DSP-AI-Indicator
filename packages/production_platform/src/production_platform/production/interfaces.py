"""Provider-neutral infrastructure ports (K1.3 + PEP-002).

Business and platform code must depend on these protocols only.
Concrete adapters live under ``production_platform.production`` (reference)
and ``production_platform.adapters`` (optional vendors).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

__all__ = [
    "AuditEventPort",
    "BackgroundTaskPort",
    "BackupPort",
    "CacheInvalidationPort",
    "CachePort",
    "ClockPort",
    "ConfigurationPort",
    "DatabasePort",
    "HealthPort",
    "JobQueuePort",
    "LockPort",
    "LoggingPort",
    "MarketCalendarPort",
    "MetricsPort",
    "QueuePort",
    "RateLimiterPort",
    "RateLimitPort",
    "Repository",
    "RepositoryFactoryPort",
    "SchedulerPort",
    "SecretProviderPort",
    "SecretRotationHookPort",
    "SecretsPort",
    "SessionPort",
    "StoragePort",
    "TracingPort",
    "TransactionPort",
    "VaultSecretsProviderPort",
]


@runtime_checkable
class LoggingPort(Protocol):
    """Structured logging sink."""

    def log(
        self,
        level: str,
        message: str,
        *,
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        """Emit one structured log record."""


@runtime_checkable
class AuditEventPort(Protocol):
    """Operational / security audit event sink (append-oriented)."""

    def emit(
        self,
        *,
        action: str,
        subject: str,
        success: bool,
        detail: str = "",
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> None:
        """Append one audit event."""

    def list_events(self, *, limit: int = 100) -> tuple[Any, ...]:
        """Return recent events (oldest → newest)."""


@runtime_checkable
class HealthPort(Protocol):
    """Liveness / readiness / health aggregation."""

    def liveness(self) -> Any:
        """Process liveness report."""

    def readiness(self) -> Any:
        """Dependency readiness report."""

    def health(self) -> Any:
        """Operational health report."""


@runtime_checkable
class MetricsPort(Protocol):
    """Metrics collection sink."""

    def incr(self, name: str, value: float = 1.0, *, tags: dict[str, str] | None = None) -> None:
        """Increment a counter."""

    def gauge(self, name: str, value: float, *, tags: dict[str, str] | None = None) -> None:
        """Set a gauge."""

    def timing(self, name: str, ms: float, *, tags: dict[str, str] | None = None) -> None:
        """Record a timing sample in milliseconds."""


@runtime_checkable
class TracingPort(Protocol):
    """Distributed tracing sink."""

    def start_span(self, name: str, *, correlation_id: str | None = None) -> str:
        """Start a span; return span_id."""

    def end_span(self, span_id: str, *, status: str = "ok") -> None:
        """End a previously started span."""

    def annotate(self, span_id: str, key: str, value: str) -> None:
        """Attach an annotation to a span."""


@runtime_checkable
class CachePort(Protocol):
    """Key/value cache abstraction."""

    def get(self, key: str) -> Any | None:
        """Return cached value or None."""

    def set(self, key: str, value: Any, *, ttl_seconds: float | None = None) -> None:
        """Store a value with optional TTL."""

    def delete(self, key: str) -> None:
        """Remove a key."""


@runtime_checkable
class CacheInvalidationPort(Protocol):
    """Cache invalidation strategy surface."""

    def invalidate(self, key: str) -> None:
        """Invalidate one key."""

    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate keys matching a glob-like pattern; return count removed."""


@runtime_checkable
class StoragePort(Protocol):
    """Opaque blob / object storage — not a relational database."""

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        """Store bytes under ``key``."""

    def get(self, key: str) -> bytes | None:
        """Fetch bytes or None when missing."""

    def delete(self, key: str) -> None:
        """Delete an object."""


@runtime_checkable
class SchedulerPort(Protocol):
    """Deferred job registration — not a workflow engine."""

    def schedule(self, job_id: str, *, delay_seconds: float = 0.0) -> None:
        """Register a job id for later execution."""

    def cancel(self, job_id: str) -> None:
        """Cancel a scheduled job if present."""

    def list_jobs(self) -> tuple[str, ...]:
        """Return known job ids."""


@runtime_checkable
class BackgroundTaskPort(Protocol):
    """Async / background task submission (architecture port)."""

    def submit(self, task_name: str, payload: Mapping[str, Any]) -> str:
        """Submit a background task; return task id."""

    def status(self, task_id: str) -> str:
        """Return task status string (queued|running|succeeded|failed|unknown)."""


@runtime_checkable
class SecretsPort(Protocol):
    """Secrets abstraction — never log returned values."""

    def get_secret(self, name: str) -> str | None:
        """Return a secret value or None when unset."""


# Stable alias (PEP-002 naming)
SecretProviderPort = SecretsPort


@runtime_checkable
class ConfigurationPort(Protocol):
    """Typed configuration access."""

    def get_environment(self) -> str:
        """Return environment profile name."""

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Return a string setting."""

    def validate(self) -> None:
        """Raise when configuration is inconsistent."""


@runtime_checkable
class ClockPort(Protocol):
    """Injectable clock for deterministic tests and IST presentation boundaries."""

    def now(self) -> datetime:
        """Return current aware datetime (UTC recommended for engines)."""


@runtime_checkable
class TransactionPort(Protocol):
    """Unit-of-work handle for a database transaction."""

    def execute(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> None:
        """Execute a statement inside the transaction."""

    def fetchall(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute and return rows as dictionaries."""

    def commit(self) -> None:
        """Commit the transaction."""

    def rollback(self) -> None:
        """Roll back the transaction."""


@runtime_checkable
class DatabasePort(Protocol):
    """SQL database abstraction — not bound to a vendor driver."""

    def ping(self) -> bool:
        """Return True when the database accepts connections."""

    def execute(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> None:
        """Execute a statement outside an explicit transaction."""

    def fetchall(
        self, statement: str, params: tuple[Any, ...] | dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute and return rows as dictionaries."""

    def transaction(self) -> Iterator[TransactionPort]:
        """Context manager yielding a transaction."""


@runtime_checkable
class Repository(Protocol):
    """Marker protocol for persistence adapters owned by bounded contexts."""

    @property
    def name(self) -> str:
        """Stable repository identity for diagnostics."""


@runtime_checkable
class RepositoryFactoryPort(Protocol):
    """Creates BC-owned repositories bound to a DatabasePort."""

    def create(self, name: str) -> Repository:
        """Return a repository instance for ``name``."""


@runtime_checkable
class RateLimitPort(Protocol):
    """Distributed or local rate-limit counter."""

    def allow(self, key: str, *, limit: int, window_seconds: float) -> bool:
        """Return True when the action is within the limit."""


# Stable alias (PEP-002 naming)
RateLimiterPort = RateLimitPort


@runtime_checkable
class LockPort(Protocol):
    """Distributed locking abstraction."""

    def acquire(self, name: str, *, ttl_seconds: float = 30.0) -> bool:
        """Try to acquire a lock; return True on success."""

    def release(self, name: str) -> None:
        """Release a previously acquired lock."""


@runtime_checkable
class SessionPort(Protocol):
    """Opaque session blob store (not browser cookies)."""

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Return session payload or None."""

    def set(
        self, session_id: str, payload: dict[str, Any], *, ttl_seconds: float | None = None
    ) -> None:
        """Store session payload."""

    def delete(self, session_id: str) -> None:
        """Delete a session."""


@runtime_checkable
class JobQueuePort(Protocol):
    """Background job queue with retry / dead-letter capability."""

    def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        *,
        delay_seconds: float = 0.0,
        max_attempts: int = 3,
    ) -> str:
        """Enqueue a job; return job id."""

    def dequeue(self, *, timeout_seconds: float = 0.0) -> dict[str, Any] | None:
        """Dequeue next job or None."""

    def ack(self, job_id: str) -> None:
        """Acknowledge successful processing."""

    def fail(self, job_id: str, *, error: str, retry: bool = True) -> None:
        """Mark failure; optionally requeue under retry policy."""

    def dead_letter(self, job_id: str) -> None:
        """Move job to dead-letter storage."""


# Stable alias (PEP-002 naming)
QueuePort = JobQueuePort


@runtime_checkable
class MarketCalendarPort(Protocol):
    """India market calendar — architecture port (ADR-PEP-0010)."""

    def is_trading_day(self, day: Any, *, exchange: str = "NSE") -> bool:
        """Return True when ``day`` is a trading session for the exchange."""

    def next_trading_day(self, day: Any, *, exchange: str = "NSE") -> Any:
        """Return the next trading day on or after ``day``."""


# RC1 M10 — re-export backup / secrets provider protocols (definitions in backup.py)
from production_platform.production.backup import (  # noqa: E402
    BackupPort,
    SecretRotationHookPort,
    VaultSecretsProviderPort,
)
