"""In-memory registries and snapshot tracker (EPIC-A003)."""

from __future__ import annotations

from threading import RLock
from typing import Any

from dsp_platform.research_monitoring.models import SnapshotTrack, utc_now

__all__ = [
    "MonitoringRegistry",
    "get_monitoring_registry",
    "reset_monitoring_registry_for_tests",
]


class MonitoringRegistry:
    """Process-local watchlist / portfolio registry + snapshot tracks.

    Stores references only — never mutates research artifacts.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._watchlist: set[str] = set()
        self._portfolios: dict[str, dict[str, Any]] = {}
        self._tracks: dict[tuple[str, str], SnapshotTrack] = {}

    def register_watchlist(self, symbols: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        with self._lock:
            for sym in symbols:
                s = str(sym).strip().upper()
                if s:
                    self._watchlist.add(s)
            return tuple(sorted(self._watchlist))

    def register_portfolio(
        self, portfolio_id: str, *, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        pid = str(portfolio_id).strip()
        if not pid:
            raise ValueError("portfolio_id is required")
        with self._lock:
            self._portfolios[pid] = {
                "portfolio_id": pid,
                "metadata": dict(metadata or {}),
                "registered_at": utc_now().isoformat(),
            }
            return dict(self._portfolios[pid])

    def track_snapshot(
        self,
        subject: str,
        *,
        subject_kind: str = "symbol",
        baseline_snapshot_id: str | None = None,
        current_snapshot_id: str | None = None,
        tracked_at: str | None = None,
    ) -> SnapshotTrack:
        subj = str(subject).strip().upper() if subject_kind == "symbol" else str(subject).strip()
        kind = str(subject_kind).strip().lower()
        if kind not in {"symbol", "portfolio"}:
            raise ValueError("subject_kind must be symbol or portfolio")
        key = (kind, subj)
        with self._lock:
            existing = self._tracks.get(key)
            track = SnapshotTrack(
                subject=subj,
                subject_kind=kind,
                baseline_snapshot_id=(
                    baseline_snapshot_id
                    if baseline_snapshot_id is not None
                    else (existing.baseline_snapshot_id if existing else None)
                ),
                current_snapshot_id=(
                    current_snapshot_id
                    if current_snapshot_id is not None
                    else (existing.current_snapshot_id if existing else None)
                ),
                tracked_at=tracked_at or utc_now().isoformat(),
            )
            self._tracks[key] = track
            return track

    def watchlist(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._watchlist))

    def portfolios(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {k: dict(v) for k, v in sorted(self._portfolios.items())}

    def tracks(self) -> tuple[SnapshotTrack, ...]:
        with self._lock:
            return tuple(
                self._tracks[k]
                for k in sorted(self._tracks.keys(), key=lambda x: (x[0], x[1]))
            )

    def get_track(self, subject: str, subject_kind: str = "symbol") -> SnapshotTrack | None:
        subj = str(subject).strip().upper() if subject_kind == "symbol" else str(subject).strip()
        with self._lock:
            return self._tracks.get((subject_kind, subj))


_REG: MonitoringRegistry | None = None


def get_monitoring_registry() -> MonitoringRegistry:
    global _REG
    if _REG is None:
        _REG = MonitoringRegistry()
    return _REG


def reset_monitoring_registry_for_tests(reg: MonitoringRegistry | None = None) -> None:
    global _REG
    _REG = reg
