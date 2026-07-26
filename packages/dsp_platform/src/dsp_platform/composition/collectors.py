"""Evidence and timing collectors for composition runs."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

__all__ = ["EvidenceCollector", "TimingCollector", "timed"]


class TimingCollector:
    def __init__(self) -> None:
        self._timings: dict[str, float] = {}

    def record(self, stage: str, elapsed_ms: float) -> None:
        self._timings[stage] = float(elapsed_ms)

    @property
    def timings(self) -> dict[str, float]:
        return dict(self._timings)

    @property
    def total_ms(self) -> float:
        return float(sum(self._timings.values()))


class EvidenceCollector:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def record(self, stage: str, payload: object | None) -> None:
        count = 0
        if payload is None:
            self._counts[stage] = 0
            return
        evidence = getattr(payload, "evidence", None)
        if evidence is not None:
            try:
                count = len(evidence)  # type: ignore[arg-type]
            except TypeError:
                count = 0
        self._counts[stage] = count

    @property
    def counts(self) -> dict[str, int]:
        return dict(self._counts)


@contextmanager
def timed() -> Iterator[list[float]]:
    """Yield a one-element list that receives elapsed_ms on exit."""
    box: list[float] = []
    start = time.perf_counter()
    try:
        yield box
    finally:
        box.append((time.perf_counter() - start) * 1000.0)
