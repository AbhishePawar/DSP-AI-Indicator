"""Enumerations for Workflow Intelligence domain models (H1.0)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "AssemblyStatus",
    "BackoffPolicy",
    "EngineStatus",
    "FailureClass",
    "ReportingStatus",
    "WorkflowState",
    "WorkflowStepState",
]


class AssemblyStatus(StrEnum):
    """Assembler outcome — structural completeness only, not execution quality."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"


class EngineStatus(StrEnum):
    """Workflow engine run completeness — not a market-quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ReportingStatus(StrEnum):
    """Reporting completeness — presentation only, not an execution score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"


class WorkflowState(StrEnum):
    """Workflow-level lifecycle state — never a business conclusion."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepState(StrEnum):
    """Step-level lifecycle state — never a BUY/SELL/HOLD conclusion."""

    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class FailureClass(StrEnum):
    """Frozen failure classification for executions."""

    PREREQUISITE = "prerequisite"
    UPSTREAM_FACADE = "upstream_facade"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    GATE = "gate"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class BackoffPolicy(StrEnum):
    """Retry backoff descriptor — adapters interpret; domain never sleeps."""

    NONE = "none"
    FIXED = "fixed"
    EXPONENTIAL = "exponential"
