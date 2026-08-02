"""P1.3 — Production monitoring helpers (ops only; no business logic)."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from typing import Any, TextIO

__all__ = [
    "ErrorSeverity",
    "PlatformLifecycleState",
    "RedactingJsonLogger",
    "classify_error",
    "get_lifecycle_state",
    "get_resource_snapshot",
    "mark_lifecycle",
    "ops_logger",
    "redact_sensitive",
    "set_lifecycle_state",
]


class ErrorSeverity(StrEnum):
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class PlatformLifecycleState(StrEnum):
    STARTUP = "startup"
    READY = "ready"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"


_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|authorization|api[_-]?key|jwt|cookie|credential)",
    re.IGNORECASE,
)
_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)

_lifecycle_lock = Lock()
_lifecycle_state = PlatformLifecycleState.STARTUP
_lifecycle_started_at = time.time()


def get_lifecycle_state() -> PlatformLifecycleState:
    with _lifecycle_lock:
        return _lifecycle_state


def set_lifecycle_state(state: PlatformLifecycleState) -> None:
    global _lifecycle_state
    with _lifecycle_lock:
        _lifecycle_state = state


def mark_lifecycle(state: PlatformLifecycleState) -> None:
    """Set lifecycle and emit a structured ops log line."""
    set_lifecycle_state(state)
    level = (
        "INFO"
        if state
        in {PlatformLifecycleState.READY, PlatformLifecycleState.DEGRADED}
        else "WARNING"
    )
    ops_logger.log(
        level,
        f"lifecycle.{state.value}",
        fields={"lifecycle": state.value},
    )


def redact_sensitive(value: Any) -> Any:
    """Recursively redact secrets from log fields. Never returns raw tokens."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if _SENSITIVE_KEY_RE.search(str(key)):
                out[str(key)] = "[REDACTED]"
            else:
                out[str(key)] = redact_sensitive(item)
        return out
    if isinstance(value, list):
        return [redact_sensitive(v) for v in value]
    if isinstance(value, str):
        return _BEARER_RE.sub(r"\1[REDACTED]", value)
    return value


def classify_error(
    exc: BaseException | None = None, *, status_code: int | None = None
) -> ErrorSeverity:
    """Classify unexpected/operational errors for monitoring."""
    if status_code is not None:
        if status_code >= 500:
            return ErrorSeverity.CRITICAL
        if status_code == 429:
            return ErrorSeverity.WARNING
        if status_code >= 400:
            return ErrorSeverity.WARNING
    if exc is None:
        return ErrorSeverity.INFO
    name = type(exc).__name__.lower()
    if "memory" in name or "systemexit" in name:
        return ErrorSeverity.CRITICAL
    if "auth" in name or "permission" in name or "forbidden" in name:
        return ErrorSeverity.WARNING
    return ErrorSeverity.ERROR


@dataclass
class RedactingJsonLogger:
    """Structured JSON logger with secret redaction (stdout)."""

    service: str = "dsp-api"
    stream: TextIO = field(default_factory=lambda: sys.stdout)
    capture: bool = True
    max_records: int = 2000
    _records: list[dict[str, Any]] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock)

    def log(
        self,
        level: str,
        message: str,
        *,
        correlation_id: str | None = None,
        fields: dict[str, Any] | None = None,
        severity: ErrorSeverity | str | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": level.strip().upper() or "INFO",
            "message": message,
            "service": self.service,
        }
        if correlation_id:
            payload["correlation_id"] = correlation_id
        if severity is not None:
            payload["severity"] = str(severity)
        if fields:
            payload["fields"] = redact_sensitive(fields)
        line = json.dumps(payload, separators=(",", ":"), sort_keys=True)
        self.stream.write(line + "\n")
        self.stream.flush()
        if self.capture:
            with self._lock:
                self._records.append(payload)
                if len(self._records) > self.max_records:
                    self._records = self._records[-self.max_records :]

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._records[-limit:])


ops_logger = RedactingJsonLogger()


def get_resource_snapshot() -> dict[str, Any]:
    """Best-effort process resource snapshot — never fails health."""
    snap: dict[str, Any] = {
        "uptime_seconds": round(time.time() - _lifecycle_started_at, 2),
        "pid": os.getpid(),
    }
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_SELF)
        snap["memory_maxrss"] = usage.ru_maxrss
        snap["cpu_user_seconds"] = round(usage.ru_utime, 3)
        snap["cpu_system_seconds"] = round(usage.ru_stime, 3)
    except Exception:
        snap["memory_maxrss"] = "Unavailable"
        snap["cpu_user_seconds"] = "Unavailable"
        snap["cpu_system_seconds"] = "Unavailable"
    try:
        import psutil  # type: ignore[import-not-found]

        proc = psutil.Process(os.getpid())
        snap["memory_rss_bytes"] = int(proc.memory_info().rss)
        snap["cpu_percent"] = float(proc.cpu_percent(interval=0.0))
    except Exception:
        snap.setdefault("memory_rss_bytes", "Unavailable")
        snap.setdefault("cpu_percent", "Unavailable")
    return snap


logging.getLogger("dsp.ops").setLevel(logging.INFO)
