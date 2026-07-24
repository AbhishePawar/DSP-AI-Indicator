"""Research artifact retention ports — architecture only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

__all__ = ["ArchivedResearch", "ResearchArchivePort"]


@dataclass(frozen=True, slots=True)
class ArchivedResearch:
    archive_id: str
    report_ref: str
    archived_at: datetime
    retention_class: str = "standard"


@runtime_checkable
class ResearchArchivePort(Protocol):
    def archive(self, report_ref: str) -> ArchivedResearch: ...

    def get(self, archive_id: str) -> ArchivedResearch: ...
