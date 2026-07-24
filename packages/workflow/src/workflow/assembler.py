"""Workflow Assembler — construction / citation bind only (H1.1).

Builds immutable WorkflowProfile (+ WorkflowReport skeleton) with execution
skeletons and initial PENDING/READY states. Never executes steps, invokes
façades, evaluates business rules, retries, or schedules.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from core.exceptions import ValidationError

from workflow.enums import AssemblyStatus, WorkflowState, WorkflowStepState
from workflow.exceptions import WorkflowError
from workflow.models import (
    ExecutionAudit,
    RetryPolicy,
    WorkflowExecution,
    WorkflowIdentity,
    WorkflowMetadata,
    WorkflowProfile,
    WorkflowReport,
    WorkflowStep,
    WorkflowSummary,
    WorkflowTransition,
)
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
)
from workflow.validation import assert_unique_workflow_ids

__all__ = [
    "AssemblyContext",
    "AssemblyResult",
    "WorkflowAssembler",
]

_ALLOWED_INPUT_STEP_STATES = frozenset(
    {WorkflowStepState.PENDING, WorkflowStepState.READY}
)
_ASSEMBLER_PROVENANCE = ("workflow.assembler",)


@dataclass(frozen=True, slots=True)
class AssemblyContext:
    """Inputs for deterministic WorkflowProfile / report skeleton construction."""

    identity: WorkflowIdentity
    metadata: WorkflowMetadata
    steps: tuple[WorkflowStep, ...]
    transitions: tuple[WorkflowTransition, ...] = ()
    analysis_refs: tuple[AnalysisReference, ...] = ()
    decision_refs: tuple[DecisionReference, ...] = ()
    industry_evidence_refs: tuple[IndustryEvidenceReference, ...] = ()
    comparison_refs: tuple[ComparisonReference, ...] = ()
    portfolio_refs: tuple[PortfolioReference, ...] = ()
    risk_refs: tuple[RiskReference, ...] = ()
    research_refs: tuple[ResearchReference, ...] = ()
    quantitative_risk_refs: tuple[QuantitativeRiskReference, ...] = ()
    recommendation_refs: tuple[RecommendationReference, ...] = ()
    created_at: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.identity is None:
            msg = "identity is required"
            raise ValidationError(msg)
        if self.metadata is None:
            msg = "metadata is required"
            raise ValidationError(msg)
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "transitions", tuple(self.transitions))
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
        created_at = (
            None if self.created_at is None else self.created_at.strip() or None
        )
        object.__setattr__(self, "created_at", created_at)
        object.__setattr__(
            self, "notes", tuple(n.strip() for n in self.notes if n.strip())
        )


@dataclass(frozen=True, slots=True)
class AssemblyResult:
    """Assembler output — structural profile / report / execution skeletons only."""

    profile: WorkflowProfile
    report: WorkflowReport
    status: AssemblyStatus
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "warnings", tuple(self.warnings))


class WorkflowAssembler:
    """Canonical constructor for immutable Workflow execution skeletons.

    Construction, reference normalization, and prerequisite validation only —
    no orchestration, façade invocation, retries, or scheduling.
    """

    def validate_inputs(self, context: AssemblyContext) -> None:
        """Reject invalid assembly inputs before construction."""
        if context.identity is None:
            msg = "missing required references: WorkflowIdentity"
            raise WorkflowError(msg)
        if not context.identity.workflow_id:
            msg = "missing required references: empty workflow_id"
            raise WorkflowError(msg)
        if not context.identity.workflow_name:
            msg = "missing required references: empty workflow_name"
            raise WorkflowError(msg)
        if context.metadata is None:
            msg = "missing required references: WorkflowMetadata"
            raise WorkflowError(msg)
        if not context.metadata.playbook_id:
            msg = "missing required references: empty playbook_id"
            raise WorkflowError(msg)
        if not context.metadata.as_of:
            msg = "missing required references: empty as_of"
            raise WorkflowError(msg)
        if not context.steps:
            msg = "missing required references: at least one WorkflowStep required"
            raise WorkflowError(msg)

        self._validate_steps(context.steps)
        self._validate_transitions(context.steps, context.transitions)
        self._validate_ref_group("analysis_refs", context.analysis_refs)
        self._validate_ref_group("decision_refs", context.decision_refs)
        self._validate_ref_group(
            "industry_evidence_refs", context.industry_evidence_refs
        )
        self._validate_ref_group("comparison_refs", context.comparison_refs)
        self._validate_ref_group("portfolio_refs", context.portfolio_refs)
        self._validate_ref_group("risk_refs", context.risk_refs)
        self._validate_ref_group("research_refs", context.research_refs)
        self._validate_ref_group(
            "quantitative_risk_refs", context.quantitative_risk_refs
        )
        self._validate_ref_group(
            "recommendation_refs", context.recommendation_refs
        )

    def assemble(self, context: AssemblyContext) -> AssemblyResult:
        """Construct immutable profile, report skeleton, and execution skeletons."""
        self.validate_inputs(context)

        warnings: list[str] = []
        created_at = context.created_at or context.identity.created_at
        if created_at is None:
            created_at = "unknown"
            warnings.append(
                "created_at missing; execution skeletons use placeholder 'unknown'."
            )

        steps = self._initialize_steps(context.steps)
        workflow_state = self._initialize_workflow_state(steps)
        executions = self._build_execution_skeletons(steps, created_at=created_at)
        audit = ExecutionAudit(entries=executions)
        summary = WorkflowSummary(
            step_count=len(steps),
            execution_count=len(executions),
            failed_execution_count=0,
            limitation_notes=(
                "Assembly skeleton only — no step execution, façade invocation, "
                "or retries. Workflow Engine (H1.2) advances state.",
                *context.notes,
            ),
        )

        profile = WorkflowProfile(
            identity=context.identity,
            state=workflow_state,
            metadata=context.metadata,
            steps=steps,
            transitions=context.transitions,
            executions=executions,
            audit=audit,
            summary=summary,
            analysis_refs=context.analysis_refs,
            decision_refs=context.decision_refs,
            industry_evidence_refs=context.industry_evidence_refs,
            comparison_refs=context.comparison_refs,
            portfolio_refs=context.portfolio_refs,
            risk_refs=context.risk_refs,
            research_refs=context.research_refs,
            quantitative_risk_refs=context.quantitative_risk_refs,
            recommendation_refs=context.recommendation_refs,
            notes=context.notes,
        )

        report = WorkflowReport(
            workflow_id=context.identity.workflow_id,
            state=workflow_state,
            summary=summary,
            metadata=context.metadata,
            as_of=context.metadata.as_of,
            steps=steps,
            transitions=context.transitions,
            executions=executions,
            audit=audit,
            analysis_refs=context.analysis_refs,
            decision_refs=context.decision_refs,
            industry_evidence_refs=context.industry_evidence_refs,
            comparison_refs=context.comparison_refs,
            portfolio_refs=context.portfolio_refs,
            risk_refs=context.risk_refs,
            research_refs=context.research_refs,
            quantitative_risk_refs=context.quantitative_risk_refs,
            recommendation_refs=context.recommendation_refs,
            limitations=(
                "WorkflowReport skeleton — no execution results yet.",
                *summary.limitation_notes,
            ),
        )

        status = AssemblyStatus.PARTIAL if warnings else AssemblyStatus.COMPLETE
        return AssemblyResult(
            profile=profile,
            report=report,
            status=status,
            warnings=tuple(warnings),
        )

    def assemble_many(
        self, contexts: tuple[AssemblyContext, ...]
    ) -> tuple[AssemblyResult, ...]:
        """Assemble many contexts; reject duplicate workflow identities."""
        assert_unique_workflow_ids(
            tuple(ctx.identity.workflow_id for ctx in contexts)
        )
        return tuple(self.assemble(context) for context in contexts)

    def _validate_steps(self, steps: tuple[WorkflowStep, ...]) -> None:
        seen: set[str] = set()
        for step in steps:
            if step is None:
                msg = "missing required references: WorkflowStep is None"
                raise WorkflowError(msg)
            if step.step_id in seen:
                msg = f"duplicate step ids: {step.step_id!r}"
                raise WorkflowError(msg)
            seen.add(step.step_id)
            if step.state not in _ALLOWED_INPUT_STEP_STATES:
                msg = (
                    f"illegal initial states: step {step.step_id!r} state "
                    f"{step.state.value!r} — assembler allows only pending/ready"
                )
                raise WorkflowError(msg)
            if step.retry_policy is not None:
                self._assert_retry_descriptor(step.retry_policy)
        for step in steps:
            for prereq in step.prerequisite_step_ids:
                if prereq not in seen:
                    msg = (
                        f"broken transitions: step {step.step_id!r} prerequisite "
                        f"{prereq!r} missing"
                    )
                    raise WorkflowError(msg)

    def _validate_transitions(
        self,
        steps: tuple[WorkflowStep, ...],
        transitions: tuple[WorkflowTransition, ...],
    ) -> None:
        step_ids = {s.step_id for s in steps}
        seen: set[str] = set()
        for transition in transitions:
            if transition is None:
                msg = "broken transitions: WorkflowTransition is None"
                raise WorkflowError(msg)
            if transition.transition_id in seen:
                msg = (
                    f"broken transitions: duplicate transition id "
                    f"{transition.transition_id!r}"
                )
                raise WorkflowError(msg)
            seen.add(transition.transition_id)
            # Illegal as *initial* targets from assembly perspective:
            # transitions themselves already enforce legal edges in __post_init__.
            if (
                transition.from_state
                in {
                    WorkflowState.RUNNING,
                    WorkflowState.COMPLETED,
                    WorkflowState.FAILED,
                    WorkflowState.CANCELLED,
                }
                and transition.to_state is WorkflowState.PENDING
            ):
                msg = (
                    f"illegal initial states: transition "
                    f"{transition.transition_id!r} cannot seed from terminal/"
                    f"running back to pending"
                )
                raise WorkflowError(msg)
            if transition.step_id is not None and transition.step_id not in step_ids:
                msg = (
                    f"broken transitions: transition {transition.transition_id!r} "
                    f"references missing step {transition.step_id!r}"
                )
                raise WorkflowError(msg)

    def _validate_ref_group(self, name: str, refs: tuple[object, ...]) -> None:
        seen_ids: set[str] = set()
        seen_reports: set[str] = set()
        for ref in refs:
            if ref is None:
                msg = f"missing required references: {name} contains None"
                raise WorkflowError(msg)
            ref_id = getattr(ref, "id", "")
            report_id = getattr(ref, "report_id", "")
            digest = getattr(ref, "digest", "")
            if not ref_id:
                msg = f"broken report ids: {name} missing id"
                raise WorkflowError(msg)
            if not report_id:
                msg = f"broken report ids: {name} missing report_id"
                raise WorkflowError(msg)
            if not digest or len(digest) < 8:
                msg = f"broken report digests: {name} digest invalid"
                raise WorkflowError(msg)
            if ref_id in seen_ids:
                msg = f"duplicate references: {name} id {ref_id!r}"
                raise WorkflowError(msg)
            if report_id in seen_reports:
                msg = f"duplicate references: {name} report_id {report_id!r}"
                raise WorkflowError(msg)
            seen_ids.add(ref_id)
            seen_reports.add(report_id)

    def _assert_retry_descriptor(self, policy: RetryPolicy) -> None:
        # RetryPolicy.__post_init__ already validates; re-surface clear assembler error.
        if policy.max_attempts < 1:
            msg = "invalid retry descriptors: max_attempts must be >= 1"
            raise WorkflowError(msg)

    def _initialize_steps(
        self, steps: tuple[WorkflowStep, ...]
    ) -> tuple[WorkflowStep, ...]:
        initialized: list[WorkflowStep] = []
        for step in steps:
            state = (
                WorkflowStepState.READY
                if not step.prerequisite_step_ids
                else WorkflowStepState.PENDING
            )
            initialized.append(replace(step, state=state))
        return tuple(initialized)

    def _initialize_workflow_state(
        self, steps: tuple[WorkflowStep, ...]
    ) -> WorkflowState:
        if all(step.state is WorkflowStepState.READY for step in steps):
            return WorkflowState.READY
        return WorkflowState.PENDING

    def _build_execution_skeletons(
        self,
        steps: tuple[WorkflowStep, ...],
        *,
        created_at: str,
    ) -> tuple[WorkflowExecution, ...]:
        executions: list[WorkflowExecution] = []
        for step in steps:
            executions.append(
                WorkflowExecution(
                    execution_id=f"dsp.workflow.exec.{step.step_id}",
                    step_id=step.step_id,
                    attempt=1,
                    status=step.state,
                    started_at=created_at,
                    ended_at=None,
                    outcome_ref_ids=(),
                    failure=None,
                    provenance=_ASSEMBLER_PROVENANCE,
                    notes=("execution skeleton — not executed",),
                )
            )
        return tuple(executions)
