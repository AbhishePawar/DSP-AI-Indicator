"""Workflow Engine tests (H1.2) — façade-only orchestration."""

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
    EngineStatus,
    FailureClass,
    RetryPolicy,
    StepFacadeResult,
    WorkflowAssembler,
    WorkflowEngine,
    WorkflowError,
    WorkflowIdentity,
    WorkflowMetadata,
    WorkflowState,
    WorkflowStep,
    WorkflowStepState,
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
    prereqs: tuple[str, ...] = (),
    max_attempts: int = 1,
    retryable: tuple[FailureClass, ...] = (),
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        step_name=step_id.rsplit(".", 1)[-1],
        capability="analysis",
        prerequisite_step_ids=prereqs,
        retry_policy=RetryPolicy(
            max_attempts=max_attempts,
            backoff_policy=BackoffPolicy.NONE,
            retryable_failure_classes=retryable,
        ),
    )


def _assemble(
    *,
    workflow_id: str = "dsp.workflow.demo",
    steps: tuple[WorkflowStep, ...] | None = None,
) -> object:
    return WorkflowAssembler().assemble(
        AssemblyContext(
            identity=_identity(workflow_id),
            metadata=_metadata(),
            steps=steps or (_step(),),
            analysis_refs=(_analysis_ref(),),
            created_at="2026-07-21T00:00:00Z",
        )
    )


class _ScriptedFacade:
    """Deterministic façade port — returns scripted outcomes per attempt."""

    def __init__(self, scripts: dict[str, list[StepFacadeResult]]) -> None:
        self._scripts = {k: list(v) for k, v in scripts.items()}
        self.calls: list[tuple[str, int]] = []

    def invoke(
        self,
        *,
        step: WorkflowStep,
        attempt: int,
        workflow_id: str,
        known_ref_ids: frozenset[str],
    ) -> StepFacadeResult:
        del workflow_id, known_ref_ids
        self.calls.append((step.step_id, attempt))
        queue = self._scripts.get(step.step_id, [])
        if not queue:
            msg = f"no scripted outcome for {step.step_id}"
            raise AssertionError(msg)
        return queue.pop(0)


def _success() -> StepFacadeResult:
    return StepFacadeResult(
        status=WorkflowStepState.SUCCEEDED,
        ended_at="2026-07-21T12:01:00Z",
        outcome_ref_ids=("dsp.workflow.ref.analysis.1",),
        provenance=("fake.facade",),
    )


def _fail(
    *,
    failure_class: FailureClass = FailureClass.UPSTREAM_FACADE,
    message: str = "façade failed",
) -> StepFacadeResult:
    return StepFacadeResult(
        status=WorkflowStepState.FAILED,
        ended_at="2026-07-21T12:01:00Z",
        failure_class=failure_class,
        failure_message=message,
        provenance=("fake.facade",),
    )


class TestEngineHappyPath:
    def test_ready_to_completed(self) -> None:
        assembly = _assemble()
        facade = _ScriptedFacade(
            {"dsp.workflow.step.analysis": [_success()]}
        )
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.COMPLETE
        assert result.profile.state is WorkflowState.COMPLETED
        assert result.profile.steps[0].state is WorkflowStepState.SUCCEEDED
        assert result.report.state is WorkflowState.COMPLETED
        assert result.execution.final_state is WorkflowState.COMPLETED
        assert facade.calls == [("dsp.workflow.step.analysis", 1)]

    def test_prerequisite_chain(self) -> None:
        steps = (
            _step(step_id="dsp.workflow.step.a"),
            _step(step_id="dsp.workflow.step.b", prereqs=("dsp.workflow.step.a",)),
        )
        assembly = _assemble(steps=steps)
        assert assembly.profile.state is WorkflowState.PENDING  # type: ignore[union-attr]
        facade = _ScriptedFacade(
            {
                "dsp.workflow.step.a": [_success()],
                "dsp.workflow.step.b": [_success()],
            }
        )
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.COMPLETE
        assert [s.state for s in result.profile.steps] == [
            WorkflowStepState.SUCCEEDED,
            WorkflowStepState.SUCCEEDED,
        ]
        assert facade.calls == [
            ("dsp.workflow.step.a", 1),
            ("dsp.workflow.step.b", 1),
        ]

    def test_retry_then_success(self) -> None:
        assembly = _assemble(
            steps=(
                _step(
                    max_attempts=2,
                    retryable=(FailureClass.TIMEOUT,),
                ),
            )
        )
        facade = _ScriptedFacade(
            {
                "dsp.workflow.step.analysis": [
                    _fail(failure_class=FailureClass.TIMEOUT, message="timeout"),
                    _success(),
                ]
            }
        )
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.COMPLETE
        assert facade.calls == [
            ("dsp.workflow.step.analysis", 1),
            ("dsp.workflow.step.analysis", 2),
        ]
        step_result = result.execution.step_results[0]
        assert len(step_result.attempts) == 2
        assert step_result.final_status is WorkflowStepState.SUCCEEDED

    def test_failed_workflow(self) -> None:
        assembly = _assemble()
        facade = _ScriptedFacade(
            {"dsp.workflow.step.analysis": [_fail()]}
        )
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.FAILED
        assert result.profile.state is WorkflowState.FAILED
        assert result.execution.step_results[0].failure is not None
        assert (
            result.execution.step_results[0].failure.failure_class
            is FailureClass.UPSTREAM_FACADE
        )

    def test_blocked(self) -> None:
        assembly = _assemble()
        facade = _ScriptedFacade(
            {
                "dsp.workflow.step.analysis": [
                    StepFacadeResult(
                        status=WorkflowStepState.BLOCKED,
                        ended_at="2026-07-21T12:01:00Z",
                        failure_class=FailureClass.GATE,
                        failure_message="awaiting approval",
                    )
                ]
            }
        )
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.BLOCKED
        assert result.profile.state is WorkflowState.BLOCKED

    def test_cancelled(self) -> None:
        assembly = _assemble()
        facade = _ScriptedFacade({})
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                cancel_requested=True,
            )
        )
        assert result.status is EngineStatus.CANCELLED
        assert result.profile.state is WorkflowState.CANCELLED
        assert facade.calls == []

    def test_skip_step(self) -> None:
        assembly = _assemble()
        facade = _ScriptedFacade({})
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                skip_step_ids=("dsp.workflow.step.analysis",),
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.COMPLETE
        assert result.profile.steps[0].state is WorkflowStepState.SKIPPED
        assert facade.calls == []

    def test_deterministic(self) -> None:
        assembly = _assemble()
        scripts = {"dsp.workflow.step.analysis": [_success()]}
        a = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=_ScriptedFacade(
                    {"dsp.workflow.step.analysis": [_success()]}
                ),
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        b = WorkflowEngine().run(
            EngineContext(
                assembly=_assemble(),  # type: ignore[arg-type]
                facade=_ScriptedFacade(scripts),
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert a.report.state == b.report.state
        assert a.profile.steps[0].state == b.profile.steps[0].state

    def test_immutable(self) -> None:
        result = WorkflowEngine().run(
            EngineContext(
                assembly=_assemble(),  # type: ignore[arg-type]
                facade=_ScriptedFacade(
                    {"dsp.workflow.step.analysis": [_success()]}
                ),
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        with pytest.raises(AttributeError):
            result.report.steps = ()  # type: ignore[misc]


class TestEngineValidation:
    def test_broken_facade_reference(self) -> None:
        assembly = _assemble()
        facade = _ScriptedFacade(
            {
                "dsp.workflow.step.analysis": [
                    StepFacadeResult(
                        status=WorkflowStepState.SUCCEEDED,
                        ended_at="2026-07-21T12:01:00Z",
                        outcome_ref_ids=("dsp.workflow.ref.missing",),
                    )
                ]
            }
        )
        with pytest.raises(WorkflowError, match="broken references"):
            WorkflowEngine().run(
                EngineContext(
                    assembly=assembly,  # type: ignore[arg-type]
                    facade=facade,
                    execution_timestamp="2026-07-21T12:00:00Z",
                )
            )

    def test_identity_mismatch(self) -> None:
        assembly = _assemble()
        other = _assemble(workflow_id="dsp.workflow.other")
        with pytest.raises(WorkflowError, match="identity mismatch"):
            WorkflowEngine().run(
                EngineContext(
                    assembly=assembly,  # type: ignore[arg-type]
                    facade=_ScriptedFacade({}),
                    profile=other.profile,  # type: ignore[union-attr]
                )
            )

    def test_non_retryable_does_not_retry(self) -> None:
        assembly = _assemble(
            steps=(
                _step(
                    max_attempts=3,
                    retryable=(FailureClass.TIMEOUT,),
                ),
            )
        )
        facade = _ScriptedFacade(
            {
                "dsp.workflow.step.analysis": [
                    _fail(failure_class=FailureClass.VALIDATION)
                ]
            }
        )
        result = WorkflowEngine().run(
            EngineContext(
                assembly=assembly,  # type: ignore[arg-type]
                facade=facade,
                execution_timestamp="2026-07-21T12:00:00Z",
            )
        )
        assert result.status is EngineStatus.FAILED
        assert facade.calls == [("dsp.workflow.step.analysis", 1)]

    def test_run_many_duplicate_ids(self) -> None:
        assembly = _assemble()
        ctx = EngineContext(
            assembly=assembly,  # type: ignore[arg-type]
            facade=_ScriptedFacade(
                {"dsp.workflow.step.analysis": [_success()]}
            ),
            execution_timestamp="2026-07-21T12:00:00Z",
        )
        with pytest.raises(WorkflowError, match="duplicate workflow ids"):
            WorkflowEngine().run_many((ctx, ctx))


class TestEngineArchitecture:
    def test_engine_forbids_upstream_imports(self) -> None:
        path = Path(__file__).resolve().parents[1] / "src" / "workflow" / "engine.py"
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
            "time",
            "asyncio",
        }
        assert names & forbidden == set()
