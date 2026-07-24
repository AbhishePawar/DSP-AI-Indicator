"""Platform lifecycle and status (K1.0).

Tracks initialization / readiness / shutdown without performing business
analysis or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from dsp_platform.platform_exceptions import PlatformLifecycleError

__all__ = [
    "PlatformLifecycle",
    "PlatformStatus",
]

_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    "created": frozenset({"initializing", "failed", "stopped"}),
    "initializing": frozenset({"ready", "degraded", "failed", "stopped"}),
    "ready": frozenset({"degraded", "stopping", "failed"}),
    "degraded": frozenset({"ready", "stopping", "failed"}),
    "stopping": frozenset({"stopped", "failed"}),
    "stopped": frozenset({"initializing", "created"}),
    "failed": frozenset({"initializing", "stopped", "created"}),
}


class PlatformStatus(StrEnum):
    """Lifecycle status for the platform integration layer."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    DEGRADED = "degraded"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class _LifecycleSnapshot:
    status: PlatformStatus
    started_at: datetime | None
    stopped_at: datetime | None
    notes: tuple[str, ...]


class PlatformLifecycle:
    """Mutable lifecycle controller used at composition / runtime edges."""

    def __init__(
        self,
        *,
        status: PlatformStatus = PlatformStatus.CREATED,
        notes: tuple[str, ...] = (),
    ) -> None:
        self._status = status
        self._started_at: datetime | None = None
        self._stopped_at: datetime | None = None
        self._notes: list[str] = [n.strip() for n in notes if n.strip()]

    @property
    def status(self) -> PlatformStatus:
        """Current lifecycle status."""
        return self._status

    @property
    def started_at(self) -> datetime | None:
        """UTC timestamp when the platform last reached READY."""
        return self._started_at

    @property
    def stopped_at(self) -> datetime | None:
        """UTC timestamp when the platform last reached STOPPED."""
        return self._stopped_at

    @property
    def notes(self) -> tuple[str, ...]:
        """Lifecycle notes (descriptive only)."""
        return tuple(self._notes)

    @property
    def is_ready(self) -> bool:
        """True when status is READY."""
        return self._status is PlatformStatus.READY

    def snapshot(self) -> _LifecycleSnapshot:
        """Immutable view of current lifecycle state."""
        return _LifecycleSnapshot(
            status=self._status,
            started_at=self._started_at,
            stopped_at=self._stopped_at,
            notes=self.notes,
        )

    def begin_initialize(self) -> None:
        """Transition CREATED/STOPPED/FAILED → INITIALIZING."""
        self._transition(PlatformStatus.INITIALIZING)

    def mark_ready(self, *, note: str | None = None) -> None:
        """Mark the platform READY."""
        self._transition(PlatformStatus.READY)
        self._started_at = datetime.now(tz=UTC)
        self._stopped_at = None
        if note:
            self._notes.append(note.strip())

    def mark_degraded(self, *, note: str | None = None) -> None:
        """Mark the platform DEGRADED (still serving limited capabilities)."""
        self._transition(PlatformStatus.DEGRADED)
        if note:
            self._notes.append(note.strip())

    def mark_failed(self, *, note: str | None = None) -> None:
        """Mark the platform FAILED."""
        self._transition(PlatformStatus.FAILED)
        if note:
            self._notes.append(note.strip())

    def begin_stop(self) -> None:
        """Transition READY/DEGRADED → STOPPING."""
        self._transition(PlatformStatus.STOPPING)

    def mark_stopped(self, *, note: str | None = None) -> None:
        """Mark the platform STOPPED."""
        self._transition(PlatformStatus.STOPPED)
        self._stopped_at = datetime.now(tz=UTC)
        if note:
            self._notes.append(note.strip())

    def ensure_ready(self) -> None:
        """Raise when the platform is not READY."""
        if self._status is not PlatformStatus.READY:
            msg = f"platform not ready: status={self._status.value}"
            raise PlatformLifecycleError(msg)

    def ensure_operational(self) -> None:
        """Raise when status is neither READY nor DEGRADED."""
        if self._status not in {PlatformStatus.READY, PlatformStatus.DEGRADED}:
            msg = f"platform not operational: status={self._status.value}"
            raise PlatformLifecycleError(msg)

    def _transition(self, target: PlatformStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS[self._status.value]
        if target.value not in allowed:
            msg = (
                f"illegal lifecycle transition: "
                f"{self._status.value!r} → {target.value!r}"
            )
            raise PlatformLifecycleError(msg)
        self._status = target
