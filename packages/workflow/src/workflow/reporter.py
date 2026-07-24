"""Workflow Reporter — presentation only (H1.3).

Organizes existing engine / report artifacts for presentation.
Never executes steps, invokes façades, recalculates, retries, or mutates
engine outputs (may append presentation-only limitation notes).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from workflow.engine import EngineResult, StepExecutionResult
from workflow.enums import ReportingStatus, WorkflowState, WorkflowStepState
from workflow.exceptions import WorkflowError
from workflow.models import (
    ExecutionAudit,
    FailureDescriptor,
    WorkflowExecution,
    WorkflowMetadata,
    WorkflowReport,
    WorkflowSummary,
)
from workflow.validation import assert_unique_workflow_ids

__all__ = [
    "ExecutionSection",
    "ReportMetadata",
    "ReportingContext",
    "ReportingResult",
    "WorkflowReporter",
]

_DEFAULT_SUMMARY_SECTIONS: tuple[str, ...] = (
    "overview",
    "state",
    "steps",
    "executions",
    "retries",
    "failures",
    "audit",
    "references",
    "metadata",
    "summary",
    "limitations",
)


@dataclass(frozen=True, slots=True)
class ExecutionSection:
    """Presentation grouping of executions for one step — values unchanged."""

    section_key: str
    title: str
    step_id: str
    executions: tuple[WorkflowExecution, ...]
    final_status: WorkflowStepState | None = None
    failure: FailureDescriptor | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "executions", tuple(self.executions))


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    """Presentation metadata — descriptive only."""

    workflow_id: str
    as_of: str
    state: WorkflowState
    step_count: int
    execution_count: int
    failed_execution_count: int
    section_keys: tuple[str, ...]
    playbook_id: str | None = None
    owner: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "section_keys", tuple(self.section_keys))


@dataclass(frozen=True, slots=True)
class ReportingContext:
    """Inputs for Workflow presentation.

    Consume ``WorkflowReport`` and/or ``EngineResult`` only.
    Never executes the engine or invokes façades.
    """

    report: WorkflowReport | None = None
    engine_result: EngineResult | None = None
    summary_sections: tuple[str, ...] | None = None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.report is None and self.engine_result is None:
            msg = "missing workflow identity: WorkflowReport or EngineResult required"
            raise WorkflowError(msg)
        if self.summary_sections is not None:
            object.__setattr__(
                self, "summary_sections", tuple(self.summary_sections)
            )
        object.__setattr__(
            self,
            "limitations",
            tuple(n.strip() for n in self.limitations if n.strip()),
        )


@dataclass(frozen=True, slots=True)
class ReportingResult:
    """Presentation output — immutable, calculation-free."""

    report: WorkflowReport
    status: ReportingStatus
    metadata: ReportMetadata
    summary: WorkflowSummary
    workflow_metadata: WorkflowMetadata
    execution_sections: tuple[ExecutionSection, ...]
    audit: ExecutionAudit
    step_results: tuple[StepExecutionResult, ...]
    failure_summary: tuple[FailureDescriptor, ...]
    retry_history: tuple[WorkflowExecution, ...]
    referenced_outcomes: tuple[str, ...]
    summary_sections: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "execution_sections", tuple(self.execution_sections)
        )
        object.__setattr__(self, "step_results", tuple(self.step_results))
        object.__setattr__(self, "failure_summary", tuple(self.failure_summary))
        object.__setattr__(self, "retry_history", tuple(self.retry_history))
        object.__setattr__(
            self, "referenced_outcomes", tuple(self.referenced_outcomes)
        )
        object.__setattr__(self, "summary_sections", tuple(self.summary_sections))
        object.__setattr__(self, "warnings", tuple(self.warnings))


class WorkflowReporter:
    """Canonical presentation layer for Workflow Intelligence.

    Formats existing artifacts — never orchestrates or invents outcomes.
    """

    def validate_inputs(self, context: ReportingContext) -> None:
        """Reject invalid presentation inputs."""
        source = self._resolve_source(context)
        if not source.workflow_id:
            msg = "missing workflow identity: workflow_id is required"
            raise WorkflowError(msg)

        if context.engine_result is not None and context.report is not None:
            if context.engine_result.workflow_id != context.report.workflow_id:
                msg = (
                    "engine/report identity mismatch: EngineResult "
                    f"{context.engine_result.workflow_id!r} does not match "
                    f"report {context.report.workflow_id!r}"
                )
                raise WorkflowError(msg)
            if context.engine_result.report.workflow_id != context.report.workflow_id:
                msg = (
                    "engine/report identity mismatch: engine.report "
                    f"{context.engine_result.report.workflow_id!r} vs "
                    f"{context.report.workflow_id!r}"
                )
                raise WorkflowError(msg)

        if source.audit is None:
            msg = "missing audit: ExecutionAudit required"
            raise WorkflowError(msg)

        self._validate_executions(source)
        self._validate_references(source)

        sections = (
            context.summary_sections
            if context.summary_sections is not None
            else _DEFAULT_SUMMARY_SECTIONS
        )
        self._reject_duplicate_summary_sections(sections)

    def report(
        self,
        context: ReportingContext | WorkflowReport | EngineResult,
    ) -> ReportingResult:
        """Build presentation artifacts from an existing report or engine result."""
        ctx = self._as_context(context)
        self.validate_inputs(ctx)
        source = self._resolve_source(ctx)
        warnings: list[str] = []

        sections = (
            ctx.summary_sections
            if ctx.summary_sections is not None
            else _DEFAULT_SUMMARY_SECTIONS
        )

        # Pass-through — preserve ordering, provenance, Decimal identity.
        summary = source.summary
        workflow_metadata = source.metadata
        audit = source.audit
        assert audit is not None

        step_results: tuple[StepExecutionResult, ...] = ()
        if ctx.engine_result is not None:
            step_results = ctx.engine_result.execution.step_results
            if ctx.report is None:
                # Prefer engine report object identity when only engine provided.
                source = ctx.engine_result.report

        execution_sections = self._build_execution_sections(
            source=source,
            step_results=step_results,
        )
        self._reject_duplicate_execution_sections(execution_sections)

        failure_summary = self._collect_failures(source, step_results)
        retry_history = self._collect_retry_history(source.executions)
        referenced_outcomes = self._collect_referenced_outcomes(source)

        if not source.executions:
            warnings.append("no executions present on report.")
        if summary.step_count == 0:
            warnings.append("summary step_count is zero.")

        limitations = tuple(
            dict.fromkeys(
                (
                    *source.limitations,
                    *summary.limitation_notes,
                    *ctx.limitations,
                    "WorkflowReport presentation only — "
                    "no orchestration performed by reporter.",
                )
            )
        )
        # Append presentation note only — do not mutate the source report object.
        presented_report = replace(source, limitations=limitations)

        metadata = ReportMetadata(
            workflow_id=source.workflow_id,
            as_of=source.as_of,
            state=source.state,
            step_count=summary.step_count,
            execution_count=summary.execution_count,
            failed_execution_count=summary.failed_execution_count,
            section_keys=sections,
            playbook_id=workflow_metadata.playbook_id,
            owner=workflow_metadata.owner,
        )

        status = (
            ReportingStatus.PARTIAL
            if warnings
            else ReportingStatus.COMPLETE
        )
        if not source.steps and not source.executions:
            status = ReportingStatus.EMPTY

        return ReportingResult(
            report=presented_report,
            status=status,
            metadata=metadata,
            summary=summary,
            workflow_metadata=workflow_metadata,
            execution_sections=execution_sections,
            audit=audit,
            step_results=step_results,
            failure_summary=failure_summary,
            retry_history=retry_history,
            referenced_outcomes=referenced_outcomes,
            summary_sections=sections,
            warnings=tuple(warnings),
        )

    def report_many(
        self,
        contexts: tuple[ReportingContext | WorkflowReport | EngineResult, ...],
    ) -> tuple[ReportingResult, ...]:
        """Present many reports; reject duplicate workflow identities."""
        resolved: list[ReportingContext] = [self._as_context(item) for item in contexts]
        assert_unique_workflow_ids(
            tuple(self._resolve_source(ctx).workflow_id for ctx in resolved)
        )
        return tuple(self.report(ctx) for ctx in resolved)

    def _as_context(
        self,
        context: ReportingContext | WorkflowReport | EngineResult,
    ) -> ReportingContext:
        if isinstance(context, ReportingContext):
            return context
        if isinstance(context, EngineResult):
            return ReportingContext(engine_result=context)
        if isinstance(context, WorkflowReport):
            return ReportingContext(report=context)
        msg = "ReportingContext, WorkflowReport, or EngineResult required"
        raise WorkflowError(msg)

    def _resolve_source(self, context: ReportingContext) -> WorkflowReport:
        if context.engine_result is not None:
            return context.engine_result.report
        if context.report is not None:
            return context.report
        msg = "missing workflow identity: no report source"
        raise WorkflowError(msg)

    def _build_execution_sections(
        self,
        *,
        source: WorkflowReport,
        step_results: tuple[StepExecutionResult, ...],
    ) -> tuple[ExecutionSection, ...]:
        by_step: dict[str, list[WorkflowExecution]] = {}
        for execution in source.executions:
            by_step.setdefault(execution.step_id, []).append(execution)

        # Preserve workflow step ordering; append any orphan execution step ids.
        ordered_step_ids: list[str] = [s.step_id for s in source.steps]
        for step_id in by_step:
            if step_id not in ordered_step_ids:
                ordered_step_ids.append(step_id)

        results_by_step = {r.step_id: r for r in step_results}
        sections: list[ExecutionSection] = []
        for step_id in ordered_step_ids:
            executions = tuple(by_step.get(step_id, ()))
            step_result = results_by_step.get(step_id)
            final_status = (
                step_result.final_status
                if step_result is not None
                else (executions[-1].status if executions else None)
            )
            failure = (
                step_result.failure
                if step_result is not None
                else next(
                    (e.failure for e in reversed(executions) if e.failure is not None),
                    None,
                )
            )
            sections.append(
                ExecutionSection(
                    section_key=f"executions.{step_id}",
                    title=f"Executions for {step_id}",
                    step_id=step_id,
                    executions=executions,
                    final_status=final_status,
                    failure=failure,
                )
            )
        return tuple(sections)

    def _collect_failures(
        self,
        source: WorkflowReport,
        step_results: tuple[StepExecutionResult, ...],
    ) -> tuple[FailureDescriptor, ...]:
        failures: list[FailureDescriptor] = []
        seen: set[tuple[str, str]] = set()
        for result in step_results:
            if result.failure is not None:
                key = (result.failure.failure_class.value, result.failure.message)
                if key not in seen:
                    seen.add(key)
                    failures.append(result.failure)
        for execution in source.executions:
            if execution.failure is None:
                continue
            key = (execution.failure.failure_class.value, execution.failure.message)
            if key not in seen:
                seen.add(key)
                failures.append(execution.failure)
        return tuple(failures)

    def _collect_retry_history(
        self, executions: tuple[WorkflowExecution, ...]
    ) -> tuple[WorkflowExecution, ...]:
        """Present retry attempts — attempt > 1 or multiple attempts per step."""
        counts: dict[str, int] = {}
        for execution in executions:
            counts[execution.step_id] = counts.get(execution.step_id, 0) + 1
        retried_steps = {sid for sid, count in counts.items() if count > 1}
        history = tuple(
            e
            for e in executions
            if e.attempt > 1 or e.step_id in retried_steps
        )
        return history

    def _collect_referenced_outcomes(self, source: WorkflowReport) -> tuple[str, ...]:
        keys: list[str] = []
        for group in (
            source.analysis_refs,
            source.decision_refs,
            source.industry_evidence_refs,
            source.comparison_refs,
            source.portfolio_refs,
            source.risk_refs,
            source.research_refs,
            source.quantitative_risk_refs,
            source.recommendation_refs,
        ):
            for ref in group:
                keys.append(ref.id)
        for execution in source.executions:
            keys.extend(execution.outcome_ref_ids)
        # Preserve first-seen ordering.
        return tuple(dict.fromkeys(keys))

    def _validate_executions(self, source: WorkflowReport) -> None:
        seen: set[str] = set()
        for execution in source.executions:
            if execution.execution_id in seen:
                msg = f"duplicate execution sections: {execution.execution_id!r}"
                raise WorkflowError(msg)
            seen.add(execution.execution_id)
            if not execution.provenance:
                msg = (
                    f"missing provenance: execution {execution.execution_id!r} "
                    "has empty provenance"
                )
                raise WorkflowError(msg)

    def _validate_references(self, source: WorkflowReport) -> None:
        known: set[str] = set()
        for group in (
            source.analysis_refs,
            source.decision_refs,
            source.industry_evidence_refs,
            source.comparison_refs,
            source.portfolio_refs,
            source.risk_refs,
            source.research_refs,
            source.quantitative_risk_refs,
            source.recommendation_refs,
        ):
            for ref in group:
                if not ref.id or not ref.report_id or not ref.digest:
                    msg = "broken references: outcome reference incomplete"
                    raise WorkflowError(msg)
                known.add(ref.id)
        for execution in source.executions:
            for ref_id in execution.outcome_ref_ids:
                if ref_id not in known:
                    msg = (
                        f"broken references: execution {execution.execution_id!r} "
                        f"cites unknown outcome {ref_id!r}"
                    )
                    raise WorkflowError(msg)

    def _reject_duplicate_summary_sections(self, sections: tuple[str, ...]) -> None:
        seen: set[str] = set()
        for raw in sections:
            key = raw.strip().lower()
            if not key:
                msg = "duplicate metadata sections: empty section key"
                raise WorkflowError(msg)
            if key in seen:
                msg = f"duplicate metadata sections: {raw!r}"
                raise WorkflowError(msg)
            seen.add(key)

    def _reject_duplicate_execution_sections(
        self, sections: tuple[ExecutionSection, ...]
    ) -> None:
        seen_keys: set[str] = set()
        seen_steps: set[str] = set()
        for section in sections:
            if section.section_key in seen_keys:
                msg = f"duplicate execution sections: {section.section_key!r}"
                raise WorkflowError(msg)
            if section.step_id in seen_steps:
                msg = f"duplicate execution sections: step {section.step_id!r}"
                raise WorkflowError(msg)
            seen_keys.add(section.section_key)
            seen_steps.add(section.step_id)
