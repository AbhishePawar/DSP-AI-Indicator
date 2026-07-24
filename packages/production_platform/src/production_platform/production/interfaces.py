"""Provider-neutral operational ports (K1.3).

Concrete adapters (Redis, Prometheus, OTel, S3, Celery, …) live outside
this package. Domain / business packages never depend on vendors here.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

__all__ = [
    "CachePort",
    "LoggingPort",
    "MetricsPort",
    "SchedulerPort",
    "SecretsPort",
    "StoragePort",
    "TracingPort",
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
class StoragePort(Protocol):
    """Opaque blob / object storage abstraction — not a database ORM."""

    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> None:
        """Store bytes under ``key``."""

    def get(self, key: str) -> bytes | None:
        """Fetch bytes or None when missing."""

    def delete(self, key: str) -> None:
        """Delete an object."""


@runtime_checkable
class SchedulerPort(Protocol):
    """Job scheduling abstraction — not a workflow engine."""

    def schedule(self, job_id: str, *, delay_seconds: float = 0.0) -> None:
        """Register / enqueue a job id for later execution by an adapter."""

    def cancel(self, job_id: str) -> None:
        """Cancel a scheduled job if present."""

    def list_jobs(self) -> tuple[str, ...]:
        """Return known job ids."""


@runtime_checkable
class SecretsPort(Protocol):
    """Secrets abstraction — never log returned values."""

    def get_secret(self, name: str) -> str | None:
        """Return a secret value or None when unset."""
