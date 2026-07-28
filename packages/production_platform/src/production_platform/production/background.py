"""Background task port — in-memory reference (PEP-002)."""

from __future__ import annotations

from threading import Lock
from typing import Any, Mapping

from production_platform.production.exceptions import ProductionError
from production_platform.production.interfaces import BackgroundTaskPort, JobQueuePort
from production_platform.production.job_queue import InMemoryJobQueuePort

__all__ = ["InMemoryBackgroundTaskPort", "ensure_background_task_port"]


class InMemoryBackgroundTaskPort:
    """Submits tasks onto a JobQueuePort — behavioural reference."""

    def __init__(self, queue: JobQueuePort | None = None) -> None:
        self._queue = queue if queue is not None else InMemoryJobQueuePort()
        self._status: dict[str, str] = {}
        self._lock = Lock()

    def submit(self, task_name: str, payload: Mapping[str, Any]) -> str:
        cleaned = task_name.strip()
        if not cleaned:
            raise ProductionError("task_name must not be empty")
        job_id = self._queue.enqueue(cleaned, dict(payload))
        with self._lock:
            self._status[job_id] = "queued"
        return job_id

    def status(self, task_id: str) -> str:
        with self._lock:
            return self._status.get(task_id, "unknown")

    def mark(self, task_id: str, state: str) -> None:
        with self._lock:
            self._status[task_id] = state


def ensure_background_task_port(port: BackgroundTaskPort | None) -> BackgroundTaskPort:
    return port if port is not None else InMemoryBackgroundTaskPort()
