"""Injectable clock (PEP-002)."""

from __future__ import annotations

from datetime import UTC, datetime

from production_platform.production.interfaces import ClockPort

__all__ = ["SystemClockPort", "FixedClockPort", "ensure_clock_port"]


class SystemClockPort:
    """Wall-clock UTC — production default."""

    def now(self) -> datetime:
        return datetime.now(tz=UTC)


class FixedClockPort:
    """Deterministic clock for tests."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=UTC)
        self._instant = instant

    def now(self) -> datetime:
        return self._instant


def ensure_clock_port(port: ClockPort | None) -> ClockPort:
    return port if port is not None else SystemClockPort()
