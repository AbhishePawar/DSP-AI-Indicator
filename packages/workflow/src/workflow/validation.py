"""Workflow validation helpers — contracts only (H1.0).

No orchestration, façade invocation, scheduling, or persistence.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.exceptions import ValidationError

from workflow.enums import (
    BackoffPolicy,
    FailureClass,
    WorkflowState,
    WorkflowStepState,
)
from workflow.exceptions import WorkflowError

__all__ = [
    "ALLOWED_STEP_TRANSITIONS",
    "ALLOWED_WORKFLOW_TRANSITIONS",
    "assert_legal_step_transition",
    "assert_legal_workflow_transition",
    "assert_unique_workflow_ids",
    "require_decimal",
    "validate_retry_policy_fields",
]

ALLOWED_WORKFLOW_TRANSITIONS: dict[WorkflowState, frozenset[WorkflowState]] = {
    WorkflowState.PENDING: frozenset(
        {WorkflowState.READY, WorkflowState.CANCELLED, WorkflowState.FAILED}
    ),
    WorkflowState.READY: frozenset(
        {
            WorkflowState.RUNNING,
            WorkflowState.BLOCKED,
            WorkflowState.CANCELLED,
            WorkflowState.FAILED,
        }
    ),
    WorkflowState.RUNNING: frozenset(
        {
            WorkflowState.BLOCKED,
            WorkflowState.COMPLETED,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.BLOCKED: frozenset(
        {
            WorkflowState.READY,
            WorkflowState.RUNNING,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        }
    ),
    WorkflowState.COMPLETED: frozenset(),
    WorkflowState.FAILED: frozenset(),
    WorkflowState.CANCELLED: frozenset(),
}

ALLOWED_STEP_TRANSITIONS: dict[WorkflowStepState, frozenset[WorkflowStepState]] = {
    WorkflowStepState.PENDING: frozenset(
        {
            WorkflowStepState.READY,
            WorkflowStepState.SKIPPED,
            WorkflowStepState.BLOCKED,
            WorkflowStepState.FAILED,
        }
    ),
    WorkflowStepState.READY: frozenset(
        {
            WorkflowStepState.RUNNING,
            WorkflowStepState.BLOCKED,
            WorkflowStepState.SKIPPED,
            WorkflowStepState.FAILED,
        }
    ),
    WorkflowStepState.RUNNING: frozenset(
        {
            WorkflowStepState.SUCCEEDED,
            WorkflowStepState.FAILED,
            WorkflowStepState.BLOCKED,
        }
    ),
    WorkflowStepState.BLOCKED: frozenset(
        {
            WorkflowStepState.READY,
            WorkflowStepState.RUNNING,
            WorkflowStepState.SKIPPED,
            WorkflowStepState.FAILED,
        }
    ),
    WorkflowStepState.SUCCEEDED: frozenset(),
    WorkflowStepState.FAILED: frozenset(
        {WorkflowStepState.READY, WorkflowStepState.RUNNING}
    ),  # retry path
    WorkflowStepState.SKIPPED: frozenset(),
}


def require_decimal(value: Any, *, field: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, Decimal):
        msg = f"{field} must be decimal.Decimal, never float or other numeric types"
        raise ValidationError(msg)
    if not value.is_finite():
        msg = f"{field} must be a finite Decimal"
        raise ValidationError(msg)
    return value


def assert_legal_workflow_transition(
    source: WorkflowState, target: WorkflowState
) -> None:
    allowed = ALLOWED_WORKFLOW_TRANSITIONS.get(source, frozenset())
    if target not in allowed:
        msg = (
            f"illegal state transitions: workflow {source.value!r} → {target.value!r}"
        )
        raise WorkflowError(msg)


def assert_legal_step_transition(
    source: WorkflowStepState, target: WorkflowStepState
) -> None:
    allowed = ALLOWED_STEP_TRANSITIONS.get(source, frozenset())
    if target not in allowed:
        msg = (
            f"illegal state transitions: step {source.value!r} → {target.value!r}"
        )
        raise WorkflowError(msg)


def assert_unique_workflow_ids(workflow_ids: tuple[str, ...]) -> None:
    """Reject duplicate workflow identities in a batch (assembler / registries)."""
    seen: set[str] = set()
    for raw in workflow_ids:
        cleaned = raw.strip().lower()
        if not cleaned:
            msg = "workflow_id must not be empty"
            raise ValidationError(msg)
        if cleaned in seen:
            msg = f"duplicate workflow ids: {cleaned!r}"
            raise WorkflowError(msg)
        seen.add(cleaned)


def validate_retry_policy_fields(
    *,
    max_attempts: int,
    backoff_policy: BackoffPolicy,
    backoff_base_ms: Decimal | None,
    retryable_failure_classes: tuple[FailureClass, ...],
) -> None:
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int):
        msg = "invalid retry configuration: max_attempts must be int"
        raise ValidationError(msg)
    if max_attempts < 1:
        msg = "negative retry counts: max_attempts must be >= 1"
        raise WorkflowError(msg)
    if backoff_policy is BackoffPolicy.NONE:
        if backoff_base_ms is not None:
            msg = (
                "invalid retry configuration: backoff_base_ms must be None "
                "when backoff_policy is NONE"
            )
            raise WorkflowError(msg)
    else:
        if backoff_base_ms is None:
            msg = (
                "invalid retry configuration: backoff_base_ms required for "
                f"{backoff_policy.value}"
            )
            raise WorkflowError(msg)
        base = require_decimal(backoff_base_ms, field="backoff_base_ms")
        if base < Decimal("0"):
            msg = "invalid retry configuration: backoff_base_ms must be >= 0"
            raise WorkflowError(msg)
    seen: set[FailureClass] = set()
    for item in retryable_failure_classes:
        if item in seen:
            msg = f"invalid retry configuration: duplicate failure class {item.value!r}"
            raise WorkflowError(msg)
        seen.add(item)
