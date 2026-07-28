"""Recommendation history + research archive reference adapters (PEP-004)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from threading import Lock

from compliance.recommendation_history import (
    RecommendationHistoryEntry,
    RecommendationHistoryPort,
)
from compliance.research_archive import ArchivedResearch, ResearchArchivePort

__all__ = [
    "InMemoryRecommendationHistoryPort",
    "InMemoryResearchArchivePort",
]


class InMemoryRecommendationHistoryPort:
    """Stores research assessments / future SEBI recommendations — reference."""

    def __init__(self) -> None:
        self._entries: list[RecommendationHistoryEntry] = []
        self._lock = Lock()

    def append(self, entry: RecommendationHistoryEntry) -> None:
        with self._lock:
            self._entries.append(entry)

    def list_for_symbol(self, symbol: str) -> tuple[RecommendationHistoryEntry, ...]:
        key = symbol.strip().upper()
        with self._lock:
            return tuple(e for e in self._entries if e.symbol.strip().upper() == key)

    def record_research_assessment(
        self,
        *,
        symbol: str,
        research_label: str,
        report_ref: str | None = None,
        horizon: str | None = None,
    ) -> RecommendationHistoryEntry:
        entry = RecommendationHistoryEntry(
            entry_id=f"rh_{uuid.uuid4().hex[:12]}",
            symbol=symbol.strip().upper(),
            action_label=research_label,
            issued_at=datetime.now(tz=UTC),
            horizon=horizon,
            target_price=None,
            report_ref=report_ref,
        )
        self.append(entry)
        return entry


class InMemoryResearchArchivePort:
    """Research artifact retention — reference with evidence metadata."""

    def __init__(self) -> None:
        self._items: dict[str, ArchivedResearch] = {}
        self._lock = Lock()

    def archive(self, report_ref: str) -> ArchivedResearch:
        item = ArchivedResearch(
            archive_id=f"ra_{uuid.uuid4().hex[:12]}",
            report_ref=report_ref,
            archived_at=datetime.now(tz=UTC),
            retention_class="research_standard",
        )
        with self._lock:
            self._items[item.archive_id] = item
        return item

    def get(self, archive_id: str) -> ArchivedResearch:
        with self._lock:
            if archive_id not in self._items:
                raise KeyError(archive_id)
            return self._items[archive_id]

    def list_all(self) -> tuple[ArchivedResearch, ...]:
        with self._lock:
            return tuple(self._items[k] for k in sorted(self._items))
