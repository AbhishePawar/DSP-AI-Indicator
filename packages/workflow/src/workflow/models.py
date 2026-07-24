"""Workflow domain models — contracts only (H1.0).

Immutable value objects and aggregate. No orchestration, façade invocation,
scheduling, or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from workflow.refs import (
    AnalysisReference,
    ComparisonReference,
    DecisionReference,
    IndustryEvidenceReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationReference,
    ResearchReference,
    RiskReference,
    _normalize_id,
)
from workflow.validation import (
    assert_legal_step_transition,
    assert_legal_workflow_transition,
    require_decimal,
    validate_retry_policy_fields,
)

__all__ = [
    "ExecutionAudit",
    "FailureDescriptor",
    "RetryPolicy",
    "WorkflowExecution",
    "WorkflowIdentity",
    "WorkflowMetadata",
    "WorkflowProfile",
    "WorkflowReport",
    "WorkflowStep",
    "WorkflowSummary",
    "WorkflowTransition",
]


def _non_empty(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class WorkflowIdentity:
    """Canonical identity of a Workflow profile / run mandate."""

    workflow_id: str
    workflow_name: str
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        workflow_id = _normalize_id(self.workflow_id, field="workflow_id")
        name = _non_empty(self.workflow_name, field="workflow_name")
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "workflow_id", workflow_id)
        object.__setattr__(self, "workflow_name", name)
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Declarative retry descriptor — adapters interpret; domain never sleeps."""

    max_attempts: int
    backoff_policy: BackoffPolicy = BackoffPolicy.NONE
    backoff_base_ms: Decimal | None = None
    retryable_failure_classes: tuple[FailureClass, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        validate_retry_policy_fields(
            max_attempts=self.max_attempts,
            backoff_policy=self.backoff_policy,
            backoff_base_ms=self.backoff_base_ms,
            retryable_failure_classes=self.retryable_failure_classes,
        )
        base = (
            None
            if self.backoff_base_ms is None
            else require_decimal(self.backoff_base_ms, field="backoff_base_ms")
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "backoff_base_ms", base)
        object.__setattr__(
            self, "retryable_failure_classes", tuple(self.retryable_failure_classes)
        )
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class FailureDescriptor:
    """Structured failure capture for an execution attempt."""

    failure_class: FailureClass
    message: str
    provenance: tuple[str, ...]
    details: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        message = _non_empty(self.message, field="message")
        if not self.provenance:
            msg = "missing provenance: FailureDescriptor requires provenance"
            raise WorkflowError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        details = tuple(d.strip() for d in self.details if d.strip())
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "details", details)


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    """Declared capability invocation unit — never executes façades."""

    step_id: str
    step_name: str
    capability: str
    state: WorkflowStepState = WorkflowStepState.PENDING
    prerequisite_step_ids: tuple[str, ...] = ()
    retry_policy: RetryPolicy | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        step_id = _normalize_id(self.step_id, field="step_id")
        step_name = _non_empty(self.step_name, field="step_name")
        capability = _non_empty(self.capability, field="capability").lower().replace(
            " ", "_"
        )
        prereqs = tuple(
            _normalize_id(s, field="prerequisite_step_ids")
            for s in self.prerequisite_step_ids
        )
        if step_id in prereqs:
            msg = f"broken transitions: step {step_id!r} cannot require itself"
            raise WorkflowError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "step_id", step_id)
        object.__setattr__(self, "step_name", step_name)
        object.__setattr__(self, "capability", capability)
        object.__setattr__(self, "prerequisite_step_ids", prereqs)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class WorkflowTransition:
    """Allowed state change + guard descriptors."""

    transition_id: str
    from_state: WorkflowState
    to_state: WorkflowState
    guard_notes: tuple[str, ...] = ()
    step_id: str | None = None
    from_step_state: WorkflowStepState | None = None
    to_step_state: WorkflowStepState | None = None

    def __post_init__(self) -> None:
        transition_id = _normalize_id(self.transition_id, field="transition_id")
        assert_legal_workflow_transition(self.from_state, self.to_state)
        step_id = (
            None
            if self.step_id is None
            else _normalize_id(self.step_id, field="step_id")
        )
        if (self.from_step_state is None) ^ (self.to_step_state is None):
            msg = (
                "broken transitions: from_step_state and to_step_state "
                "must both be set or both omitted"
            )
            raise WorkflowError(msg)
        if self.from_step_state is not None and self.to_step_state is not None:
            assert_legal_step_transition(self.from_step_state, self.to_step_state)
            if step_id is None:
                msg = "broken transitions: step_id required for step-level transition"
                raise WorkflowError(msg)
        guards = tuple(g.strip() for g in self.guard_notes if g.strip())
        object.__setattr__(self, "transition_id", transition_id)
        object.__setattr__(self, "step_id", step_id)
        object.__setattr__(self, "guard_notes", guards)


@dataclass(frozen=True, slots=True)
class WorkflowExecution:
    """Immutable record of a step attempt — no façade invocation here."""

    execution_id: str
    step_id: str
    attempt: int
    status: WorkflowStepState
    started_at: str
    ended_at: str | None = None
    outcome_ref_ids: tuple[str, ...] = ()
    failure: FailureDescriptor | None = None
    provenance: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        execution_id = _normalize_id(self.execution_id, field="execution_id")
        step_id = _normalize_id(self.step_id, field="step_id")
        if isinstance(self.attempt, bool) or not isinstance(self.attempt, int):
            msg = "attempt must be int"
            raise ValidationError(msg)
        if self.attempt < 1:
            msg = "negative retry counts: attempt must be >= 1"
            raise WorkflowError(msg)
        started_at = _non_empty(self.started_at, field="started_at")
        ended_at = (
            None if self.ended_at is None else self.ended_at.strip() or None
        )
        if not self.provenance:
            msg = "missing provenance: WorkflowExecution requires provenance"
            raise WorkflowError(msg)
        provenance = tuple(_non_empty(p, field="provenance") for p in self.provenance)
        outcome_ref_ids = tuple(
            _normalize_id(r, field="outcome_ref_ids") for r in self.outcome_ref_ids
        )
        if self.status is WorkflowStepState.FAILED and self.failure is None:
            msg = "missing provenance: FAILED execution requires FailureDescriptor"
            raise WorkflowError(msg)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "execution_id", execution_id)
        object.__setattr__(self, "step_id", step_id)
        object.__setattr__(self, "started_at", started_at)
        object.__setattr__(self, "ended_at", ended_at)
        object.__setattr__(self, "outcome_ref_ids", outcome_ref_ids)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class ExecutionAudit:
    """Ordered audit trail of executions — descriptive only."""

    entries: tuple[WorkflowExecution, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        entries = _unique_executions(self.entries)
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class WorkflowMetadata:
    """Descriptive workflow metadata — not a business score."""

    playbook_id: str
    as_of: str
    owner: str | None = None
    tags: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        playbook_id = _normalize_id(self.playbook_id, field="playbook_id")
        as_of = _non_empty(self.as_of, field="as_of")
        owner = None if self.owner is None else self.owner.strip() or None
        tags = tuple(t.strip() for t in self.tags if t.strip())
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "playbook_id", playbook_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class WorkflowSummary:
    """High-level workflow summary — descriptive counts only."""

    step_count: int
    execution_count: int = 0
    failed_execution_count: int = 0
    limitation_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("step_count", "execution_count", "failed_execution_count"):
            if getattr(self, name) < 0:
                msg = "counts must be >= 0"
                raise ValidationError(msg)
        limitations = tuple(
            n.strip() for n in self.limitation_notes if n.strip()
        )
        object.__setattr__(self, "limitation_notes", limitations)


@dataclass(frozen=True, slots=True)
class WorkflowReport:
    """Canonical immutable Workflow presentation / audit snapshot."""

    workflow_id: str
    state: WorkflowState
    summary: WorkflowSummary
    metadata: WorkflowMetadata
    as_of: str
    steps: tuple[WorkflowStep, ...] = ()
    transitions: tuple[WorkflowTransition, ...] = ()
    executions: tuple[WorkflowExecution, ...] = ()
    audit: ExecutionAudit | None = None
    analysis_refs: tuple[AnalysisReference, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    industry_evidence_refs: tuple[IndustryEvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_refs: tuple[PortfolioReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    recommendation_refs: tuple[RecommendationReference, ...] = ()
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        workflow_id = _normalize_id(self.workflow_id, field="workflow_id")
        as_of = _non_empty(self.as_of, field="as_of")
        steps = _unique_steps(self.steps)
        transitions = _unique_transitions(self.transitions)
        executions = _unique_executions(self.executions)
        _validate_transition_step_links(steps, transitions)
        _validate_execution_step_links(steps, executions)
        refs = _collect_ref_ids(
            analysis_refs=self.analysis_refs,
            decision_refs=self.decision_refs,
            industry_evidence_refs=self.industry_evidence_refs,
            comparison_refs=self.comparison_refs,
            portfolio_refs=self.portfolio_refs,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
            recommendation_refs=self.recommendation_refs,
        )
        _validate_execution_outcome_refs(executions, refs)
        _reject_duplicate_report_refs(
            analysis_refs=self.analysis_refs,
            decision_refs=self.decision_refs,
            industry_evidence_refs=self.industry_evidence_refs,
            comparison_refs=self.comparison_refs,
            portfolio_refs=self.portfolio_refs,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
            recommendation_refs=self.recommendation_refs,
        )
        limitations = tuple(n.strip() for n in self.limitations if n.strip())
        object.__setattr__(self, "workflow_id", workflow_id)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "transitions", transitions)
        object.__setattr__(self, "executions", executions)
        object.__setattr__(self, "analysis_refs", tuple(self.analysis_refs))
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(
            self, "industry_evidence_refs", tuple(self.industry_evidence_refs)
        )
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "portfolio_refs", tuple(self.portfolio_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        object.__setattr__(
            self, "recommendation_refs", tuple(self.recommendation_refs)
        )
        object.__setattr__(self, "limitations", limitations)


@dataclass(frozen=True, slots=True)
class WorkflowProfile:
    """Aggregate root — cites upstream outcomes; owns workflow artifacts only."""

    identity: WorkflowIdentity
    state: WorkflowState
    metadata: WorkflowMetadata
    steps: tuple[WorkflowStep, ...] = ()
    transitions: tuple[WorkflowTransition, ...] = ()
    executions: tuple[WorkflowExecution, ...] = ()
    audit: ExecutionAudit | None = None
    summary: WorkflowSummary | None = None
    analysis_refs: tuple[AnalysisReference, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    industry_evidence_refs: tuple[IndustryEvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_refs: tuple[PortfolioReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    recommendation_refs: tuple[RecommendationReference, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "missing identity: WorkflowIdentity is required"
            raise WorkflowError(msg)
        steps = _unique_steps(self.steps)
        transitions = _unique_transitions(self.transitions)
        executions = _unique_executions(self.executions)
        _validate_transition_step_links(steps, transitions)
        _validate_execution_step_links(steps, executions)
        refs = _collect_ref_ids(
            analysis_refs=self.analysis_refs,
            decision_refs=self.decision_refs,
            industry_evidence_refs=self.industry_evidence_refs,
            comparison_refs=self.comparison_refs,
            portfolio_refs=self.portfolio_refs,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
            recommendation_refs=self.recommendation_refs,
        )
        _validate_execution_outcome_refs(executions, refs)
        _reject_duplicate_report_refs(
            analysis_refs=self.analysis_refs,
            decision_refs=self.decision_refs,
            industry_evidence_refs=self.industry_evidence_refs,
            comparison_refs=self.comparison_refs,
            portfolio_refs=self.portfolio_refs,
            risk_refs=self.risk_refs,
            research_refs=self.research_refs,
            quantitative_risk_refs=self.quantitative_risk_refs,
            recommendation_refs=self.recommendation_refs,
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "transitions", transitions)
        object.__setattr__(self, "executions", executions)
        object.__setattr__(self, "analysis_refs", tuple(self.analysis_refs))
        object.__setattr__(self, "decision_refs", tuple(self.decision_refs))
        object.__setattr__(
            self, "industry_evidence_refs", tuple(self.industry_evidence_refs)
        )
        object.__setattr__(self, "comparison_refs", tuple(self.comparison_refs))
        object.__setattr__(self, "portfolio_refs", tuple(self.portfolio_refs))
        object.__setattr__(self, "risk_refs", tuple(self.risk_refs))
        object.__setattr__(self, "research_refs", tuple(self.research_refs))
        object.__setattr__(
            self, "quantitative_risk_refs", tuple(self.quantitative_risk_refs)
        )
        object.__setattr__(
            self, "recommendation_refs", tuple(self.recommendation_refs)
        )
        object.__setattr__(self, "notes", notes)

    @property
    def workflow_id(self) -> str:
        return self.identity.workflow_id


def _unique_steps(items: tuple[WorkflowStep, ...]) -> tuple[WorkflowStep, ...]:
    seen: set[str] = set()
    for item in items:
        if item.step_id in seen:
            msg = f"duplicate step ids: {item.step_id!r}"
            raise WorkflowError(msg)
        seen.add(item.step_id)
    for item in items:
        for prereq in item.prerequisite_step_ids:
            if prereq not in seen:
                msg = (
                    f"broken transitions: step {item.step_id!r} prerequisite "
                    f"{prereq!r} missing"
                )
                raise WorkflowError(msg)
    return tuple(items)


def _unique_transitions(
    items: tuple[WorkflowTransition, ...],
) -> tuple[WorkflowTransition, ...]:
    seen: set[str] = set()
    for item in items:
        if item.transition_id in seen:
            msg = f"broken transitions: duplicate transition id {item.transition_id!r}"
            raise WorkflowError(msg)
        seen.add(item.transition_id)
    return tuple(items)


def _unique_executions(
    items: tuple[WorkflowExecution, ...],
) -> tuple[WorkflowExecution, ...]:
    seen: set[str] = set()
    for item in items:
        if item.execution_id in seen:
            msg = f"duplicate execution ids: {item.execution_id!r}"
            raise WorkflowError(msg)
        seen.add(item.execution_id)
    return tuple(items)


def _validate_transition_step_links(
    steps: tuple[WorkflowStep, ...],
    transitions: tuple[WorkflowTransition, ...],
) -> None:
    step_ids = {s.step_id for s in steps}
    for transition in transitions:
        if transition.step_id is not None and transition.step_id not in step_ids:
            msg = (
                f"broken transitions: transition {transition.transition_id!r} "
                f"references missing step {transition.step_id!r}"
            )
            raise WorkflowError(msg)


def _validate_execution_step_links(
    steps: tuple[WorkflowStep, ...],
    executions: tuple[WorkflowExecution, ...],
) -> None:
    step_ids = {s.step_id for s in steps}
    for execution in executions:
        if execution.step_id not in step_ids:
            msg = (
                f"broken transitions: execution {execution.execution_id!r} "
                f"references missing step {execution.step_id!r}"
            )
            raise WorkflowError(msg)


def _collect_ref_ids(**groups: tuple[Any, ...]) -> frozenset[str]:
    keys: set[str] = set()
    for items in groups.values():
        for ref in items:
            keys.add(ref.id)
    return frozenset(keys)


def _validate_execution_outcome_refs(
    executions: tuple[WorkflowExecution, ...],
    known_ref_ids: frozenset[str],
) -> None:
    for execution in executions:
        for ref_id in execution.outcome_ref_ids:
            if ref_id not in known_ref_ids:
                msg = (
                    f"broken references: execution {execution.execution_id!r} "
                    f"references unknown outcome {ref_id!r}"
                )
                raise WorkflowError(msg)


def _reject_duplicate_report_refs(**groups: tuple[Any, ...]) -> None:
    for name, items in groups.items():
        seen_ids: set[str] = set()
        seen_reports: set[str] = set()
        for ref in items:
            if ref.id in seen_ids:
                msg = f"duplicate report references: {name} id {ref.id!r}"
                raise WorkflowError(msg)
            if ref.report_id in seen_reports:
                msg = (
                    f"duplicate report references: {name} report_id "
                    f"{ref.report_id!r}"
                )
                raise WorkflowError(msg)
            seen_ids.add(ref.id)
            seen_reports.add(ref.report_id)
