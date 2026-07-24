"""Recommendation history archive — SEBI Mode activation surface (future)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

__all__ = ["RecommendationHistoryEntry", "RecommendationHistoryPort"]


@dataclass(frozen=True, slots=True)
class RecommendationHistoryEntry:
    """Historical recommendation row — stored only when SEBI Mode is active."""

    entry_id: str
    symbol: str
    action_label: str
    issued_at: datetime
    horizon: str | None = None
    target_price: str | None = None
    report_ref: str | None = None


@runtime_checkable
class RecommendationHistoryPort(Protocol):
    def append(self, entry: RecommendationHistoryEntry) -> None: ...

    def list_for_symbol(self, symbol: str) -> tuple[RecommendationHistoryEntry, ...]: ...
