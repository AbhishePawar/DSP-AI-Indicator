"""Methodology disclosure stubs — architecture only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ["MethodologyNote", "MethodologyPort"]


@dataclass(frozen=True, slots=True)
class MethodologyNote:
    note_id: str
    title: str
    summary: str
    version: str = "1"


@runtime_checkable
class MethodologyPort(Protocol):
    def publish(self) -> tuple[MethodologyNote, ...]: ...
