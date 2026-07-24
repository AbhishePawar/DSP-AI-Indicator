"""Scheduler — in-memory provider-neutral adapter."""

from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock

from production_platform.production.exceptions import ProductionError
from production_platform.production.interfaces import SchedulerPort

__all__ = ["InMemorySchedulerPort", "ScheduledJob"]


@dataclass(frozen=True, slots=True)
class ScheduledJob:
    job_id: str
    run_at_monotonic: float


class InMemorySchedulerPort:
    """Process-local job registry — not Celery / RQ."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._lock = Lock()

    def schedule(self, job_id: str, *, delay_seconds: float = 0.0) -> None:
        cleaned = job_id.strip()
        if not cleaned:
            msg = "job_id must not be empty"
            raise ProductionError(msg)
        if delay_seconds < 0:
            msg = "delay_seconds must be non-negative"
            raise ProductionError(msg)
        with self._lock:
            self._jobs[cleaned] = ScheduledJob(
                job_id=cleaned,
                run_at_monotonic=time.monotonic() + float(delay_seconds),
            )

    def cancel(self, job_id: str) -> None:
        with self._lock:
            self._jobs.pop(job_id.strip(), None)

    def list_jobs(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._jobs))


def ensure_scheduler_port(port: SchedulerPort | None) -> SchedulerPort:
    return port if port is not None else InMemorySchedulerPort()
