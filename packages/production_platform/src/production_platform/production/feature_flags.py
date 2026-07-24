"""Feature flags — in-memory manager."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from production_platform.production.exceptions import ProductionError

__all__ = ["FeatureFlag", "FeatureFlagManager"]


@dataclass(frozen=True, slots=True)
class FeatureFlag:
    name: str
    enabled: bool
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            msg = "feature flag name must not be empty"
            raise ProductionError(msg)


class FeatureFlagManager:
    """Process-local feature flag registry."""

    def __init__(self, initial: dict[str, bool] | None = None) -> None:
        self._flags: dict[str, FeatureFlag] = {}
        self._lock = Lock()
        for name, enabled in (initial or {}).items():
            self.set(name, enabled)

    def set(
        self, name: str, enabled: bool, *, description: str = ""
    ) -> FeatureFlag:
        flag = FeatureFlag(
            name=name.strip(), enabled=enabled, description=description
        )
        with self._lock:
            self._flags[flag.name.lower()] = flag
        return flag

    def is_enabled(self, name: str, *, default: bool = False) -> bool:
        with self._lock:
            flag = self._flags.get(name.strip().lower())
        return default if flag is None else flag.enabled

    def get(self, name: str) -> FeatureFlag | None:
        with self._lock:
            return self._flags.get(name.strip().lower())

    def list_flags(self) -> tuple[FeatureFlag, ...]:
        with self._lock:
            return tuple(
                self._flags[k] for k in sorted(self._flags.keys())
            )

    def as_dict(self) -> dict[str, bool]:
        return {f.name: f.enabled for f in self.list_flags()}
