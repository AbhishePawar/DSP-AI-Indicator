"""Enumerations for Research domain models (structure only)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ResearchAssemblyStatus",
    "ResearchConflictSeverity",
    "ResearchCoverageStatus",
    "ResearchGapStatus",
    "ResearchPriorityLevel",
    "ResearchReportingStatus",
    "ResearchSynthesisStatus",
]


class ResearchPriorityLevel(StrEnum):
    """Categorical investigation priority — never a numeric score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResearchGapStatus(StrEnum):
    """Knowledge-gap lifecycle — descriptive only; Research never resolves."""

    OPEN = "open"
    PARTIAL = "partial"
    RESOLVED = "resolved"


class ResearchConflictSeverity(StrEnum):
    """Declared conflict severity — descriptive only."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


class ResearchCoverageStatus(StrEnum):
    """Knowledge-coverage completeness — not a quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class ResearchAssemblyStatus(StrEnum):
    """Assembler outcome — structural completeness only, not synthesis quality."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"


class ResearchSynthesisStatus(StrEnum):
    """Synthesis completeness — knowledge orchestration only, not a score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"


class ResearchReportingStatus(StrEnum):
    """Reporting completeness — presentation only, not a research score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"
