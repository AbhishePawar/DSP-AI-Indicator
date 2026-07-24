"""Workflow Reporter tests (H1.3) — presentation only."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from workflow import (
    AnalysisReference,
    AssemblyContext,
    BackoffPolicy,
    EngineContext,
    FailureClass,
    ReportingContext,
    ReportingStatus,
    RetryPolicy,
    StepFacadeResult,
    WorkflowAssembler,
    WorkflowEngine,
    WorkflowError,
    WorkflowIdentity,
    WorkflowMetadata,
    WorkflowReport,
    WorkflowReporter,
    WorkflowState,
    WorkflowStep,
    WorkflowStepState,
    WorkflowSummary,
)


def _identity(workflow_id: str = "dsp.workflow.demo") -> WorkflowIdentity:
    return WorkflowIdentity(
        workflow_id=workflow_id,
        workflow_name="Demo Workflow",
        created_at="2026-07-21T00:00:00Z",
    )


def _metadata() -> WorkflowMetadata:
    return WorkflowMetadata(
        playbook_id="dsp.workflow.playbook.demo",
        as_of="2026-07-21",
        owner="platform",
    )


def _analysis_ref() -> AnalysisReference:
    return AnalysisReference(
        id="dsp.workflow.ref.analysis.1",
        report_id="dsp.analysis.report.1",
        version="1.0.0",
        digest="abcdef0123456789",
        status="complete",
        generated_at="2026-07-21T12:00:00Z",
    )


def _step(
    *,
    step_id: str = "dsp.workflow.step.analysis",
    max_attempts: int = 1,
    retryable: tuple[FailureClass, ...] = (),
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        step_name=step_id.rsplit(".", 1)[-1],
        capability="analysis",
        retry_policy=RetryPolicy(
            max_attempts=max_attempts,
            backoff_policy=BackoffPolicy.NONE,
            retryable_failure_classes=retryable,
        ),
    )


class _ScriptedFacade:
    def __init__(self, scripts: dict[str, list[StepFacadeResult]]) -> None:
        self._scripts = {k: list(v) for k, v in scripts.items()}

    def invoke(
        self,
        *,
        step: WorkflowStep,
        attempt: int,
        workflow_id: str,
        known_ref_ids: frozenset[str],
    ) -> StepFacadeResult:
        del attempt, workflow_id, known_ref_ids
        queue = self._scripts[step.step_id]
        return queue.pop(0)


def _success() -> StepFacadeResult:
    return StepFacadeResult(
        status=WorkflowStepState.SUCCEEDED,
        ended_at="2026-07-21T12:01:00Z",
        outcome_ref_ids=("dsp.workflow.ref.analysis.1",),
        provenance=("fake.facade",),
    )


def _fail_timeout() -> StepFacadeResult:
    return StepFacadeResult(
        status=WorkflowStepState.FAILED,
        ended_at="2026-07-21T12:00:30Z",
        failure_class=FailureClass.TIMEOUT,
        failure_message="timeout",
        provenance=("fake.facade",),
    )


def _engine_result(*, with_retry: bool = False):
    steps = (
        (
            _step(
                max_attempts=2,
                retryable=(FailureClass.TIMEOUT,),
            ),
        )
        if with_retry
        else (_step(),)
    )
    assembly = WorkflowAssembler().assemble(
        AssemblyContext(
            identity=_identity(),
            metadata=_metadata(),
            steps=steps,
            analysis_refs=(_analysis_ref(),),
            created_at="2026-07-21T00:00:00Z",
        )
    )
    scripts: dict[str, list[StepFacadeResult]] = {
        "dsp.workflow.step.analysis": (
            [_fail_timeout(), _success()] if with_retry else [_success()]
        )
    }
    return WorkflowEngine().run(
        EngineContext(
            assembly=assembly,
            facade=_ScriptedFacade(scripts),
            execution_timestamp="2026-07-21T12:00:00Z",
        )
    )


class TestReporterHappyPath:
    def test_from_engine_result(self) -> None:
        engine_result = _engine_result()
        result = WorkflowReporter().report(engine_result)
        assert result.status is ReportingStatus.COMPLETE
        assert result.metadata.workflow_id == "dsp.workflow.demo"
        assert result.metadata.state is WorkflowState.COMPLETED
        assert result.execution_sections
        assert result.audit is not None
        assert result.step_results
        assert result.referenced_outcomes
        assert "executions" in result.summary_sections
        assert any("presentation only" in n for n in result.report.limitations)

    def test_from_report(self) -> None:
        engine_result = _engine_result()
        result = WorkflowReporter().report(engine_result.report)
        assert result.status is ReportingStatus.COMPLETE
        assert result.report.executions == engine_result.report.executions

    def test_preserves_execution_ordering(self) -> None:
        engine_result = _engine_result()
        result = WorkflowReporter().report(engine_result)
        assert result.report.executions == engine_result.report.executions
        assert result.audit.entries == engine_result.report.audit.entries  # type: ignore[union-attr]

    def test_preserves_retry_policy_decimal_identity(self) -> None:
        assembly = WorkflowAssembler().assemble(
            AssemblyContext(
                identity=_identity(),
                metadata=_metadata(),
                steps=(
                    WorkflowStep(
                        step_id="dsp.workflow.step.analysis",
                        step_name="analysis",
                        capability="analysis",
                        retry_policy=RetryPolicy(
                            max_attempts=2,
                            backoff_policy=BackoffPolicy.FIXED,
                            backoff_base_ms=Decimal("100"),
                            retryable_failure_classes=(FailureClass.TIMEOUT,),
                        ),
                    ),
                ),
                analysis_refs=(_analysis_ref(),),
                created_at="2026-07-21T00:00:00Z",
            )
        )
        source_ms = assembly.profile.steps[0].retry_policy.backoff_base_ms  # type: ignore[union-attr]
        engine_result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,
                facade=_ScriptedFacade(
                    {"dsp.workflow.step.analysis": [_success()]}
                ),
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        result = WorkflowReporter().report(engine_result)
        presented = result.report.steps[0].retry_policy
        assert presented is not None
        assert presented.backoff_base_ms is source_ms

    def test_retry_history_presented(self) -> None:
        engine_result = _engine_result(with_retry=True)
        result = WorkflowReporter().report(engine_result)
        assert result.retry_history
        assert any(e.attempt > 1 for e in result.retry_history)
        assert result.failure_summary  # timeout failure retained in history path

    def test_does_not_mutate_source_report(self) -> None:
        engine_result = _engine_result()
        original_limitations = engine_result.report.limitations
        result = WorkflowReporter().report(engine_result)
        assert engine_result.report.limitations == original_limitations
        assert result.report is not engine_result.report
        assert len(result.report.limitations) >= len(original_limitations)

    def test_immutable(self) -> None:
        result = WorkflowReporter().report(_engine_result())
        with pytest.raises(AttributeError):
            result.execution_sections = ()  # type: ignore[misc]


class TestReporterValidation:
    def test_missing_inputs(self) -> None:
        with pytest.raises(WorkflowError, match="missing workflow identity"):
            ReportingContext()

    def test_duplicate_metadata_sections(self) -> None:
        with pytest.raises(WorkflowError, match="duplicate metadata sections"):
            WorkflowReporter().report(
                ReportingContext(
                    engine_result=_engine_result(),
                    summary_sections=("overview", "Overview"),
                )
            )

    def test_identity_mismatch(self) -> None:
        engine_result = _engine_result()
        other = WorkflowReport(
            workflow_id="dsp.workflow.other",
            state=WorkflowState.COMPLETED,
            summary=WorkflowSummary(step_count=0),
            metadata=_metadata(),
            as_of="2026-07-21",
            audit=engine_result.report.audit,
        )
        with pytest.raises(WorkflowError, match="identity mismatch"):
            WorkflowReporter().report(
                ReportingContext(engine_result=engine_result, report=other)
            )

    def test_report_many_duplicate(self) -> None:
        engine_result = _engine_result()
        with pytest.raises(WorkflowError, match="duplicate workflow ids"):
            WorkflowReporter().report_many((engine_result, engine_result))


class TestReporterNoOrchestration:
    def test_reporter_forbids_execution_side_effects(self) -> None:
        source = (
            Path(__file__).resolve().parents[1] / "src" / "workflow" / "reporter.py"
        ).read_text(encoding="utf-8")
        assert "WorkflowEngine" not in source
        assert "SubsystemFacadePort" not in source
        assert "time.sleep" not in source
        assert "quantize" not in source

    def test_reporter_forbids_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1] / "src" / "workflow" / "reporter.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    names.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names.add(node.module.split(".", 1)[0])
        forbidden = {
            "orchestration",
            "recommendation",
            "portfolio",
            "risk",
            "research",
            "quantitative_risk",
            "dsp_platform",
        }
        assert names & forbidden == set()
