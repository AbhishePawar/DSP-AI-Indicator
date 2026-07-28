"""Background job queue — in-memory architecture (PEP-002 / ADR-PEP-0013)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from production_platform.production.exceptions import ProductionError
from production_platform.production.interfaces import JobQueuePort

__all__ = [
    "InMemoryJobQueuePort",
    "JobRecord",
    "RetryPolicy",
    "ensure_job_queue_port",
]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry / dead-letter policy for background jobs."""

    max_attempts: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    multiplier: float = 2.0

    def delay_for_attempt(self, attempt: int) -> float:
        if attempt <= 1:
            return self.base_delay_seconds
        delay = self.base_delay_seconds * (self.multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    payload: dict[str, Any]
    attempts: int = 0
    max_attempts: int = 3
    available_at: float = 0.0
    last_error: str | None = None
    status: str = "queued"


class InMemoryJobQueuePort:
    """Process-local queue with retry + dead-letter — not Celery / SQS."""

    def __init__(self, *, retry_policy: RetryPolicy | None = None) -> None:
        self._policy = retry_policy or RetryPolicy()
        self._jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []
        self._dead: dict[str, JobRecord] = {}
        self._inflight: dict[str, JobRecord] = {}
        self._lock = Lock()

    def enqueue(
        self,
        job_type: str,
        payload: dict[str, Any],
        *,
        delay_seconds: float = 0.0,
        max_attempts: int = 3,
    ) -> str:
        cleaned = job_type.strip()
        if not cleaned:
            raise ProductionError("job_type must not be empty")
        job_id = str(uuid.uuid4())
        record = JobRecord(
            job_id=job_id,
            job_type=cleaned,
            payload=dict(payload),
            max_attempts=max(1, int(max_attempts)),
            available_at=time.monotonic() + float(delay_seconds),
        )
        with self._lock:
            self._jobs[job_id] = record
            self._order.append(job_id)
        return job_id

    def dequeue(self, *, timeout_seconds: float = 0.0) -> dict[str, Any] | None:
        _ = timeout_seconds
        now = time.monotonic()
        with self._lock:
            for job_id in list(self._order):
                record = self._jobs.get(job_id)
                if record is None:
                    continue
                if record.available_at > now:
                    continue
                self._order.remove(job_id)
                del self._jobs[job_id]
                record.attempts += 1
                record.status = "inflight"
                self._inflight[job_id] = record
                return {
                    "job_id": record.job_id,
                    "job_type": record.job_type,
                    "payload": dict(record.payload),
                    "attempts": record.attempts,
                    "max_attempts": record.max_attempts,
                }
        return None

    def ack(self, job_id: str) -> None:
        with self._lock:
            self._inflight.pop(job_id, None)

    def fail(self, job_id: str, *, error: str, retry: bool = True) -> None:
        with self._lock:
            record = self._inflight.pop(job_id, None)
            if record is None:
                return
            record.last_error = error
            if retry and record.attempts < record.max_attempts:
                delay = self._policy.delay_for_attempt(record.attempts)
                record.available_at = time.monotonic() + delay
                record.status = "queued"
                self._jobs[job_id] = record
                self._order.append(job_id)
                return
            record.status = "dead"
            self._dead[job_id] = record

    def dead_letter(self, job_id: str) -> None:
        with self._lock:
            record = self._inflight.pop(job_id, None) or self._jobs.pop(job_id, None)
            if record is None:
                return
            if job_id in self._order:
                self._order.remove(job_id)
            record.status = "dead"
            self._dead[job_id] = record

    def list_dead_letters(self) -> tuple[JobRecord, ...]:
        with self._lock:
            return tuple(self._dead[k] for k in sorted(self._dead))


def ensure_job_queue_port(port: JobQueuePort | None) -> JobQueuePort:
    return port if port is not None else InMemoryJobQueuePort()
