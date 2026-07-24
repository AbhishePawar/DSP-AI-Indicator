"""Mandatory disclosure interfaces — architecture only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ["Disclosure", "DisclosurePort"]


@dataclass(frozen=True, slots=True)
class Disclosure:
    disclosure_id: str
    title: str
    body: str
    audience: str = "retail"
    mandatory: bool = True
    version: str = "1"


@runtime_checkable
class DisclosurePort(Protocol):
    def list_active(self, *, mode: str) -> tuple[Disclosure, ...]: ...
