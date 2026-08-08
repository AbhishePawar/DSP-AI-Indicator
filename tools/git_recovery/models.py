"""Data models for Git Recovery Manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Risk(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    IGNORE = "IGNORE"


@dataclass(frozen=True)
class ChangedFile:
    """One porcelain entry."""

    status: str
    path: str
    original_path: str | None = None  # rename source

    @property
    def is_untracked(self) -> bool:
        return self.status == "??"

    @property
    def is_deleted(self) -> bool:
        return "D" in self.status


@dataclass
class RecoveryGroup:
    """Logical commit unit."""

    key: str
    title: str
    purpose: str
    files: list[ChangedFile] = field(default_factory=list)
    suggested_message: str = ""
    depends_on: list[str] = field(default_factory=list)
    risk: Risk = Risk.MEDIUM
    epic: str = ""
    package: str = ""
    action: str = "COMMIT"  # COMMIT | REVIEW | IGNORE

    @property
    def paths(self) -> list[str]:
        return [f.path for f in self.files]


@dataclass
class RecoveryPlan:
    """Full recovery plan for a dirty repository."""

    branch: str
    remote: str
    total_files: int
    groups: list[RecoveryGroup]
    ignored: list[ChangedFile] = field(default_factory=list)
    generated_at: str = ""

    @property
    def commit_groups(self) -> list[RecoveryGroup]:
        return [g for g in self.groups if g.action != "IGNORE" and g.files]
