"""Workflow Engine — façade-only orchestration (H1.2).

Advances workflow / step state, invokes subsystem façades through a local port,
records audits / retries / failures, and emits an updated WorkflowReport.
Never performs financial analysis, modifies upstream reports, sleeps, or
schedules work.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol, runtime_checkable

from workflow.assembler import AssemblyResult
from workflow.enums import EngineStatus, FailureClass, WorkflowState, WorkflowStepState
from workflow.exceptions import WorkflowError
from workflow.models import (
    ExecutionAudit,
    FailureDescriptor,
    RetryPolicy,
    WorkflowExecution,
    WorkflowProfile,
    WorkflowReport,
    WorkflowStep,
    WorkflowSummary,
)
from workflow.validation import (
    assert_legal_step_transition,
    assert_legal_workflow_transition,
    assert_unique_workflow_ids,
)

__all__ = [
    "EngineContext",
    "EngineResult",
    "ExecutionResult",
    "StepExecutionResult",
    "StepFacadeResult",
    "SubsystemFacadePort",
    "WorkflowEngine",
]

_ENGINE_PROVENANCE = ("workflow.engine",)
_TERMINAL_STEP_FROM_FACADE = frozenset(
    {
        WorkflowStepState.SUCCEEDED,
        WorkflowStepState.FAILED,
        WorkflowStepState.BLOCKED,
        WorkflowStepState.SKIPPED,
    }
)


@dataclass(frozen=True, slots=True)
class StepFacadeResult:
    """Outcome from a subsystem façade adapter — never primary analysis."""

    status: WorkflowStepState
    ended_at: str
    outcome_ref_ids: tuple[str, ...] = ()
    failure_class: FailureClass | None = None
    failure_message: str | None = None
    provenance: tuple[str, ...] = ("subsystem.facade",)
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in _TERMINAL_STEP_FROM_FACADE:
            msg = (
                f"illegal state transitions: façade status {self.status.value!r} "
                "must be succeeded/failed/blocked/skipped"
            )
            raise WorkflowError(msg)
        ended_at = self.ended_at.strip()
        if not ended_at:
            msg = "broken provenance: StepFacadeResult.ended_at required"
            raise WorkflowError(msg)
        object.__setattr__(self, "ended_at", ended_at)
        object.__setattr__(
            self,
            "outcome_ref_ids",
            tuple(r.strip().lower() for r in self.outcome_ref_ids if r.strip()),
        )
        object.__setattr__(
            self,
            "provenance",
            tuple(p.strip() for p in self.provenance if p.strip()) or ("subsystem.facade",),
        )
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )
        if self.status is WorkflowStepState.FAILED:
            if self.failure_class is None or not (self.failure_message or "").strip():
                msg = (
                    "missing provenance: FAILED façade result requires "
                    "failure_class and failure_message"
                )
                raise WorkflowError(msg)
            if self.failure_class not in FailureClass:
                msg = f"unsupported failure class: {self.failure_class!r}"
                raise WorkflowError(msg)


@runtime_checkable
class SubsystemFacadePort(Protocol):
    """Package-local port — adapters invoke upstream public façades only."""

    def invoke(
        self,
        *,
        step: WorkflowStep,
        attempt: int,
        workflow_id: str,
        known_ref_ids: frozenset[str],
    ) -> StepFacadeResult:
        """Execute one step attempt via a subsystem façade."""


@dataclass(frozen=True, slots=True)
class EngineContext:
    """Inputs for deterministic workflow orchestration."""

    assembly: AssemblyResult
    facade: SubsystemFacadePort
    profile: WorkflowProfile | None = None
    execution_timestamp: str | None = None
    cancel_requested: bool = False
    skip_step_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.assembly is None:
            msg = "AssemblyResult is required"
            raise WorkflowError(msg)
        if self.facade is None:
            msg = "SubsystemFacadePort is required"
            raise WorkflowError(msg)
        timestamp = (
            None
            if self.execution_timestamp is None
            else self.execution_timestamp.strip() or None
        )
        object.__setattr__(self, "execution_timestamp", timestamp)
        object.__setattr__(
            self,
            "skip_step_ids",
            tuple(s.strip().lower() for s in self.skip_step_ids if s.strip()),
        )


@dataclass(frozen=True, slots=True)
class StepExecutionResult:
    """Immutable per-step orchestration outcome."""

    step_id: str
    final_status: WorkflowStepState
    attempts: tuple[WorkflowExecution, ...]
    outcome_ref_ids: tuple[str, ...] = ()
    failure: FailureDescriptor | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "attempts", tuple(self.attempts))
        object.__setattr__(self, "outcome_ref_ids", tuple(self.outcome_ref_ids))


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Immutable workflow-level orchestration outcome."""

    workflow_id: str
    final_state: WorkflowState
    step_results: tuple[StepExecutionResult, ...]
    audit: ExecutionAudit
    executions: tuple[WorkflowExecution, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_results", tuple(self.step_results))
        object.__setattr__(self, "executions", tuple(self.executions))
        seen: set[str] = set()
        for item in self.executions:
            if item.execution_id in seen:
                msg = f"duplicate execution results: {item.execution_id!r}"
                raise WorkflowError(msg)
            seen.add(item.execution_id)


@dataclass(frozen=True, slots=True)
class EngineResult:
    """Immutable engine output — updated profile / report + execution results."""

    workflow_id: str
    status: EngineStatus
    profile: WorkflowProfile
    report: WorkflowReport
    execution: ExecutionResult
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class WorkflowEngine:
    """Canonical façade-only workflow orchestration layer."""

    def validate_inputs(self, context: EngineContext) -> None:
        """Reject invalid orchestration inputs."""
        if context is None or context.assembly is None:
            msg = "EngineContext.assembly is required"
            raise WorkflowError(msg)
        if context.facade is None:
            msg = "missing execution: SubsystemFacadePort required"
            raise WorkflowError(msg)
        profile = context.profile or context.assembly.profile
        report = context.assembly.report
        if profile is None:
            msg = "missing workflow: WorkflowProfile required"
            raise WorkflowError(msg)
        if report is None:
            msg = "missing workflow: WorkflowReport required"
            raise WorkflowError(msg)
        if profile.workflow_id != report.workflow_id:
            msg = (
                "engine/report identity mismatch: "
                f"profile {profile.workflow_id!r} vs report {report.workflow_id!r}"
            )
            raise WorkflowError(msg)
        if (
            context.profile is not None
            and context.profile.workflow_id != context.assembly.profile.workflow_id
        ):
            msg = (
                "engine/report identity mismatch: context profile "
                f"{context.profile.workflow_id!r} vs assembly "
                f"{context.assembly.profile.workflow_id!r}"
            )
            raise WorkflowError(msg)
        if not profile.steps:
            msg = "missing workflow: steps required"
            raise WorkflowError(msg)
        if not profile.executions:
            msg = "missing execution: assembled WorkflowExecution skeletons required"
            raise WorkflowError(msg)
        if profile.audit is None:
            msg = "missing audit: ExecutionAudit required"
            raise WorkflowError(msg)
        if profile.state not in {WorkflowState.PENDING, WorkflowState.READY}:
            msg = (
                f"illegal state transitions: engine start requires pending/ready, "
                f"got {profile.state.value!r}"
            )
            raise WorkflowError(msg)
        for step in profile.steps:
            if step.state not in {
                WorkflowStepState.PENDING,
                WorkflowStepState.READY,
            }:
                msg = (
                    f"illegal state transitions: step {step.step_id!r} start state "
                    f"{step.state.value!r}"
                )
                raise WorkflowError(msg)

    def run(self, context: EngineContext | AssemblyResult) -> EngineResult:
        """Orchestrate assembled workflow via façade port; emit updated report."""
        if isinstance(context, AssemblyResult):
            msg = "EngineContext with SubsystemFacadePort is required"
            raise WorkflowError(msg)
        self.validate_inputs(context)
        profile = context.profile or context.assembly.profile
        report = context.assembly.report
        timestamp = context.execution_timestamp or report.as_of or "unknown"
        warnings: list[str] = []
        if context.execution_timestamp is None:
            warnings.append(
                "execution_timestamp missing; using report.as_of for attempt times."
            )

        known_refs = _collect_known_ref_ids(profile)
        steps = {s.step_id: s for s in profile.steps}
        step_states = {s.step_id: s.state for s in profile.steps}
        workflow_state = profile.state
        audit_entries: list[WorkflowExecution] = list(profile.audit.entries)
        step_results: list[StepExecutionResult] = []
        skip_ids = frozenset(context.skip_step_ids)

        if context.cancel_requested:
            workflow_state = self._transition_workflow(
                workflow_state, WorkflowState.CANCELLED
            )
            execution = ExecutionResult(
                workflow_id=profile.workflow_id,
                final_state=workflow_state,
                step_results=(),
                audit=ExecutionAudit(
                    entries=tuple(audit_entries),
                    notes=("cancelled before step execution",),
                ),
                executions=tuple(audit_entries),
            )
            return self._finalize(
                profile=profile,
                report=report,
                workflow_state=workflow_state,
                steps=steps,
                step_states=step_states,
                execution=execution,
                status=EngineStatus.CANCELLED,
                warnings=tuple(warnings),
            )

        # Promote PENDING → READY when prerequisites already satisfied.
        step_states, steps = self._promote_ready_steps(steps, step_states)
        if workflow_state is WorkflowState.PENDING:
            workflow_state = self._transition_workflow(
                workflow_state, WorkflowState.READY
            )

        workflow_state = self._transition_workflow(
            workflow_state, WorkflowState.RUNNING
        )

        ordered_ids = tuple(s.step_id for s in profile.steps)
        terminal_block = False
        terminal_fail = False

        for step_id in ordered_ids:
            step_states, steps = self._promote_ready_steps(steps, step_states)
            step = steps[step_id]
            state = step_states[step_id]

            if state in {
                WorkflowStepState.SUCCEEDED,
                WorkflowStepState.SKIPPED,
            }:
                continue

            if not self._prerequisites_satisfied(step, step_states):
                failure = FailureDescriptor(
                    failure_class=FailureClass.PREREQUISITE,
                    message=(
                        f"prerequisites not satisfied for step {step_id!r}: "
                        f"{step.prerequisite_step_ids}"
                    ),
                    provenance=_ENGINE_PROVENANCE,
                )
                exec_rec = self._record_execution(
                    step_id=step_id,
                    attempt=1,
                    status=WorkflowStepState.FAILED,
                    started_at=timestamp,
                    ended_at=timestamp,
                    failure=failure,
                    notes=("prerequisite gate",),
                )
                audit_entries.append(exec_rec)
                step_states[step_id] = WorkflowStepState.FAILED
                steps[step_id] = replace(step, state=WorkflowStepState.FAILED)
                step_results.append(
                    StepExecutionResult(
                        step_id=step_id,
                        final_status=WorkflowStepState.FAILED,
                        attempts=(exec_rec,),
                        failure=failure,
                    )
                )
                terminal_fail = True
                break

            if state is WorkflowStepState.PENDING:
                assert_legal_step_transition(state, WorkflowStepState.READY)
                state = WorkflowStepState.READY
                step_states[step_id] = state
                steps[step_id] = replace(step, state=state)
                step = steps[step_id]

            if step_id in skip_ids:
                assert_legal_step_transition(state, WorkflowStepState.SKIPPED)
                exec_rec = self._record_execution(
                    step_id=step_id,
                    attempt=1,
                    status=WorkflowStepState.SKIPPED,
                    started_at=timestamp,
                    ended_at=timestamp,
                    notes=("skipped by engine context",),
                )
                audit_entries.append(exec_rec)
                step_states[step_id] = WorkflowStepState.SKIPPED
                steps[step_id] = replace(step, state=WorkflowStepState.SKIPPED)
                step_results.append(
                    StepExecutionResult(
                        step_id=step_id,
                        final_status=WorkflowStepState.SKIPPED,
                        attempts=(exec_rec,),
                    )
                )
                continue

            result, new_entries, blocked = self._execute_step_with_retries(
                step=step,
                facade=context.facade,
                workflow_id=profile.workflow_id,
                known_ref_ids=known_refs,
                started_at=timestamp,
            )
            audit_entries.extend(new_entries)
            step_states[step_id] = result.final_status
            steps[step_id] = replace(step, state=result.final_status)
            step_results.append(result)
            if blocked:
                terminal_block = True
                break
            if result.final_status is WorkflowStepState.FAILED:
                terminal_fail = True
                break

        if terminal_block:
            workflow_state = self._transition_workflow(
                workflow_state, WorkflowState.BLOCKED
            )
            engine_status = EngineStatus.BLOCKED
        elif terminal_fail:
            workflow_state = self._transition_workflow(
                workflow_state, WorkflowState.FAILED
            )
            engine_status = EngineStatus.FAILED
        else:
            workflow_state = self._transition_workflow(
                workflow_state, WorkflowState.COMPLETED
            )
            engine_status = EngineStatus.COMPLETE

        # Deduplicate audit: keep assembler skeletons + new attempts (unique ids).
        audit = ExecutionAudit(
            entries=tuple(audit_entries),
            notes=("engine orchestration audit",),
        )
        execution = ExecutionResult(
            workflow_id=profile.workflow_id,
            final_state=workflow_state,
            step_results=tuple(step_results),
            audit=audit,
            executions=tuple(audit_entries),
        )
        return self._finalize(
            profile=profile,
            report=report,
            workflow_state=workflow_state,
            steps=steps,
            step_states=step_states,
            execution=execution,
            status=engine_status,
            warnings=tuple(warnings),
        )

    def run_many(
        self, contexts: tuple[EngineContext, ...]
    ) -> tuple[EngineResult, ...]:
        """Run many contexts; reject duplicate workflow identities."""
        assert_unique_workflow_ids(
            tuple(
                (c.profile or c.assembly.profile).workflow_id for c in contexts
            )
        )
        return tuple(self.run(context) for context in contexts)

    def _execute_step_with_retries(
        self,
        *,
        step: WorkflowStep,
        facade: SubsystemFacadePort,
        workflow_id: str,
        known_ref_ids: frozenset[str],
        started_at: str,
    ) -> tuple[StepExecutionResult, list[WorkflowExecution], bool]:
        policy = step.retry_policy or RetryPolicy(max_attempts=1)
        max_attempts = policy.max_attempts
        attempts: list[WorkflowExecution] = []
        attempt = 1
        blocked = False
        final_status = WorkflowStepState.FAILED
        failure: FailureDescriptor | None = None
        outcome_ref_ids: tuple[str, ...] = ()

        while True:
            if attempt > max_attempts:
                msg = (
                    f"retry overflow: step {step.step_id!r} attempt {attempt} "
                    f"exceeds max_attempts {max_attempts}"
                )
                raise WorkflowError(msg)

            if attempt == 1:
                assert_legal_step_transition(
                    WorkflowStepState.READY, WorkflowStepState.RUNNING
                )
            else:
                assert_legal_step_transition(
                    WorkflowStepState.FAILED, WorkflowStepState.RUNNING
                )

            facade_result = facade.invoke(
                step=step,
                attempt=attempt,
                workflow_id=workflow_id,
                known_ref_ids=known_ref_ids,
            )
            self._validate_facade_refs(facade_result, known_ref_ids)

            if facade_result.status is WorkflowStepState.SUCCEEDED:
                assert_legal_step_transition(
                    WorkflowStepState.RUNNING, WorkflowStepState.SUCCEEDED
                )
                exec_rec = self._record_execution(
                    step_id=step.step_id,
                    attempt=attempt,
                    status=WorkflowStepState.SUCCEEDED,
                    started_at=started_at,
                    ended_at=facade_result.ended_at,
                    outcome_ref_ids=facade_result.outcome_ref_ids,
                    provenance=(*_ENGINE_PROVENANCE, *facade_result.provenance),
                    notes=facade_result.notes,
                )
                attempts.append(exec_rec)
                final_status = WorkflowStepState.SUCCEEDED
                outcome_ref_ids = facade_result.outcome_ref_ids
                failure = None
                break

            if facade_result.status is WorkflowStepState.SKIPPED:
                assert_legal_step_transition(
                    WorkflowStepState.READY, WorkflowStepState.SKIPPED
                )
                # Façade may skip without entering RUNNING — record SKIPPED.
                exec_rec = self._record_execution(
                    step_id=step.step_id,
                    attempt=attempt,
                    status=WorkflowStepState.SKIPPED,
                    started_at=started_at,
                    ended_at=facade_result.ended_at,
                    provenance=(*_ENGINE_PROVENANCE, *facade_result.provenance),
                    notes=facade_result.notes,
                )
                attempts.append(exec_rec)
                final_status = WorkflowStepState.SKIPPED
                break

            if facade_result.status is WorkflowStepState.BLOCKED:
                assert_legal_step_transition(
                    WorkflowStepState.RUNNING, WorkflowStepState.BLOCKED
                )
                failure = FailureDescriptor(
                    failure_class=facade_result.failure_class or FailureClass.GATE,
                    message=facade_result.failure_message or "blocked by façade gate",
                    provenance=(*_ENGINE_PROVENANCE, *facade_result.provenance),
                )
                exec_rec = self._record_execution(
                    step_id=step.step_id,
                    attempt=attempt,
                    status=WorkflowStepState.BLOCKED,
                    started_at=started_at,
                    ended_at=facade_result.ended_at,
                    failure=failure,
                    provenance=(*_ENGINE_PROVENANCE, *facade_result.provenance),
                    notes=facade_result.notes,
                )
                attempts.append(exec_rec)
                final_status = WorkflowStepState.BLOCKED
                blocked = True
                break

            # FAILED path
            assert_legal_step_transition(
                WorkflowStepState.RUNNING, WorkflowStepState.FAILED
            )
            assert facade_result.failure_class is not None
            failure = FailureDescriptor(
                failure_class=facade_result.failure_class,
                message=(facade_result.failure_message or "upstream façade failure"),
                provenance=(*_ENGINE_PROVENANCE, *facade_result.provenance),
            )
            exec_rec = self._record_execution(
                step_id=step.step_id,
                attempt=attempt,
                status=WorkflowStepState.FAILED,
                started_at=started_at,
                ended_at=facade_result.ended_at,
                failure=failure,
                provenance=(*_ENGINE_PROVENANCE, *facade_result.provenance),
                notes=(*facade_result.notes, f"attempt {attempt}"),
            )
            attempts.append(exec_rec)
            final_status = WorkflowStepState.FAILED

            retryable = (
                facade_result.failure_class in policy.retryable_failure_classes
            )
            if not retryable or attempt >= max_attempts:
                break
            # Honor RetryPolicy by recording another attempt immediately.
            # Never sleep / schedule — adapters own delay semantics.
            attempt += 1
            if attempt > max_attempts:
                msg = (
                    f"retry overflow: step {step.step_id!r} would exceed "
                    f"max_attempts {max_attempts}"
                )
                raise WorkflowError(msg)

        return (
            StepExecutionResult(
                step_id=step.step_id,
                final_status=final_status,
                attempts=tuple(attempts),
                outcome_ref_ids=outcome_ref_ids,
                failure=failure if final_status is WorkflowStepState.FAILED else (
                    failure if final_status is WorkflowStepState.BLOCKED else None
                ),
            ),
            attempts,
            blocked,
        )

    def _finalize(
        self,
        *,
        profile: WorkflowProfile,
        report: WorkflowReport,
        workflow_state: WorkflowState,
        steps: dict[str, WorkflowStep],
        step_states: dict[str, WorkflowStepState],
        execution: ExecutionResult,
        status: EngineStatus,
        warnings: tuple[str, ...],
    ) -> EngineResult:
        del step_states  # states already applied onto steps
        ordered_steps = tuple(steps[s.step_id] for s in profile.steps)
        failed_count = sum(
            1
            for e in execution.executions
            if e.status is WorkflowStepState.FAILED
        )
        summary = WorkflowSummary(
            step_count=len(ordered_steps),
            execution_count=len(execution.executions),
            failed_execution_count=failed_count,
            limitation_notes=(
                "Workflow Engine (H1.2) façade-only orchestration — "
                "no business analysis, no upstream report mutation.",
                *(profile.summary.limitation_notes if profile.summary else ()),
            ),
        )
        new_profile = WorkflowProfile(
            identity=profile.identity,
            state=workflow_state,
            metadata=profile.metadata,
            steps=ordered_steps,
            transitions=profile.transitions,
            executions=execution.executions,
            audit=execution.audit,
            summary=summary,
            analysis_refs=profile.analysis_refs,
            decision_refs=profile.decision_refs,
            industry_evidence_refs=profile.industry_evidence_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_refs=profile.portfolio_refs,
            risk_refs=profile.risk_refs,
            research_refs=profile.research_refs,
            quantitative_risk_refs=profile.quantitative_risk_refs,
            recommendation_refs=profile.recommendation_refs,
            notes=profile.notes,
        )
        new_report = WorkflowReport(
            workflow_id=profile.workflow_id,
            state=workflow_state,
            summary=summary,
            metadata=profile.metadata,
            as_of=report.as_of,
            steps=ordered_steps,
            transitions=profile.transitions,
            executions=execution.executions,
            audit=execution.audit,
            analysis_refs=profile.analysis_refs,
            decision_refs=profile.decision_refs,
            industry_evidence_refs=profile.industry_evidence_refs,
            comparison_refs=profile.comparison_refs,
            portfolio_refs=profile.portfolio_refs,
            risk_refs=profile.risk_refs,
            research_refs=profile.research_refs,
            quantitative_risk_refs=profile.quantitative_risk_refs,
            recommendation_refs=profile.recommendation_refs,
            limitations=(
                "WorkflowReport populated by Workflow Engine — "
                "Reporter (H1.3) may refine presentation.",
                *summary.limitation_notes,
                *report.limitations,
            ),
        )
        return EngineResult(
            workflow_id=profile.workflow_id,
            status=status,
            profile=new_profile,
            report=new_report,
            execution=execution,
            warnings=warnings,
        )

    def _transition_workflow(
        self, source: WorkflowState, target: WorkflowState
    ) -> WorkflowState:
        assert_legal_workflow_transition(source, target)
        return target

    def _promote_ready_steps(
        self,
        steps: dict[str, WorkflowStep],
        step_states: dict[str, WorkflowStepState],
    ) -> tuple[dict[str, WorkflowStepState], dict[str, WorkflowStep]]:
        updated_states = dict(step_states)
        updated_steps = dict(steps)
        for step_id, step in steps.items():
            if updated_states[step_id] is not WorkflowStepState.PENDING:
                continue
            if self._prerequisites_satisfied(step, updated_states):
                assert_legal_step_transition(
                    WorkflowStepState.PENDING, WorkflowStepState.READY
                )
                updated_states[step_id] = WorkflowStepState.READY
                updated_steps[step_id] = replace(step, state=WorkflowStepState.READY)
        return updated_states, updated_steps

    def _prerequisites_satisfied(
        self,
        step: WorkflowStep,
        step_states: dict[str, WorkflowStepState],
    ) -> bool:
        for prereq in step.prerequisite_step_ids:
            if step_states.get(prereq) not in {
                WorkflowStepState.SUCCEEDED,
                WorkflowStepState.SKIPPED,
            }:
                return False
        return True

    def _record_execution(
        self,
        *,
        step_id: str,
        attempt: int,
        status: WorkflowStepState,
        started_at: str,
        ended_at: str | None,
        outcome_ref_ids: tuple[str, ...] = (),
        failure: FailureDescriptor | None = None,
        provenance: tuple[str, ...] = _ENGINE_PROVENANCE,
        notes: tuple[str, ...] = (),
    ) -> WorkflowExecution:
        return WorkflowExecution(
            execution_id=f"dsp.workflow.exec.{step_id}.attempt.{attempt}",
            step_id=step_id,
            attempt=attempt,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            outcome_ref_ids=outcome_ref_ids,
            failure=failure,
            provenance=provenance,
            notes=notes,
        )

    def _validate_facade_refs(
        self, result: StepFacadeResult, known_ref_ids: frozenset[str]
    ) -> None:
        for ref_id in result.outcome_ref_ids:
            if ref_id not in known_ref_ids:
                msg = f"broken references: façade cited unknown outcome {ref_id!r}"
                raise WorkflowError(msg)


def _collect_known_ref_ids(profile: WorkflowProfile) -> frozenset[str]:
    keys: set[str] = set()
    for group in (
        profile.analysis_refs,
        profile.decision_refs,
        profile.industry_evidence_refs,
        profile.comparison_refs,
        profile.portfolio_refs,
        profile.risk_refs,
        profile.research_refs,
        profile.quantitative_risk_refs,
        profile.recommendation_refs,
    ):
        for ref in group:
            keys.add(ref.id)
    return frozenset(keys)
