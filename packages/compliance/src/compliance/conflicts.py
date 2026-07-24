"""Conflict-of-interest records — architecture only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ["ConflictRecord", "ConflictPort"]


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    conflict_id: str
    subject: str
    description: str
    severity: str = "disclosed"
    active: bool = True


@runtime_checkable
class ConflictPort(Protocol):
    def list_for_subject(self, subject: str) -> tuple[ConflictRecord, ...]: ...
