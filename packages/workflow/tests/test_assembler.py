"""Workflow Assembler tests (H1.1) — construction only."""

from __future__ import annotations

import ast
from decimal import Decimal
from pathlib import Path

import pytest

from workflow import (
    AnalysisReference,
    AssemblyContext,
    AssemblyStatus,
    BackoffPolicy,
    ComparisonReference,
    DecisionReference,
    FailureClass,
    IndustryEvidenceReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationReference,
    ResearchReference,
    RetryPolicy,
    RiskReference,
    WorkflowAssembler,
    WorkflowError,
    WorkflowIdentity,
    WorkflowMetadata,
    WorkflowState,
    WorkflowStep,
    WorkflowStepState,
    WorkflowTransition,
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


def _ref(
    cls: type,
    *,
    id_: str,
    report_id: str,
) -> object:
    return cls(
        id=id_,
        report_id=report_id,
        version="1.0.0",
        digest="abcdef0123456789",
        status="complete",
        generated_at="2026-07-21T12:00:00Z",
    )


def _step(
    *,
    step_id: str = "dsp.workflow.step.analysis",
    prereqs: tuple[str, ...] = (),
    state: WorkflowStepState = WorkflowStepState.PENDING,
    retry: RetryPolicy | None = None,
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        step_name=step_id.rsplit(".", 1)[-1],
        capability="analysis",
        state=state,
        prerequisite_step_ids=prereqs,
        retry_policy=retry
        or RetryPolicy(
            max_attempts=2,
            backoff_policy=BackoffPolicy.FIXED,
            backoff_base_ms=Decimal("50"),
            retryable_failure_classes=(FailureClass.TIMEOUT,),
        ),
    )


def _ctx(
    *,
    workflow_id: str = "dsp.workflow.demo",
    steps: tuple[WorkflowStep, ...] | None = None,
    transitions: tuple[WorkflowTransition, ...] = (),
    created_at: str | None = "2026-07-21T00:00:00Z",
    with_refs: bool = True,
) -> AssemblyContext:
    analysis = _ref(
        AnalysisReference,
        id_="dsp.workflow.ref.analysis.1",
        report_id="dsp.analysis.report.1",
    )
    kwargs: dict = {
        "identity": _identity(workflow_id),
        "metadata": _metadata(),
        "steps": (_step(),) if steps is None else steps,
        "transitions": transitions,
        "created_at": created_at,
    }
    if with_refs:
        kwargs.update(
            {
                "analysis_refs": (analysis,),
                "decision_refs": (
                    _ref(
                        DecisionReference,
                        id_="dsp.workflow.ref.decision.1",
                        report_id="dsp.decision.report.1",
                    ),
                ),
                "industry_evidence_refs": (
                    _ref(
                        IndustryEvidenceReference,
                        id_="dsp.workflow.ref.ief.1",
                        report_id="dsp.ief.report.1",
                    ),
                ),
                "comparison_refs": (
                    _ref(
                        ComparisonReference,
                        id_="dsp.workflow.ref.comparison.1",
                        report_id="dsp.comparison.report.1",
                    ),
                ),
                "portfolio_refs": (
                    _ref(
                        PortfolioReference,
                        id_="dsp.workflow.ref.portfolio.1",
                        report_id="dsp.portfolio.report.1",
                    ),
                ),
                "risk_refs": (
                    _ref(
                        RiskReference,
                        id_="dsp.workflow.ref.risk.1",
                        report_id="dsp.risk.report.1",
                    ),
                ),
                "research_refs": (
                    _ref(
                        ResearchReference,
                        id_="dsp.workflow.ref.research.1",
                        report_id="dsp.research.report.1",
                    ),
                ),
                "quantitative_risk_refs": (
                    _ref(
                        QuantitativeRiskReference,
                        id_="dsp.workflow.ref.qrisk.1",
                        report_id="dsp.qrisk.report.1",
                    ),
                ),
                "recommendation_refs": (
                    _ref(
                        RecommendationReference,
                        id_="dsp.workflow.ref.recommendation.1",
                        report_id="dsp.recommendation.report.1",
                    ),
                ),
            }
        )
    return AssemblyContext(**kwargs)  # type: ignore[arg-type]


class TestAssemblyHappyPath:
    def test_ready_when_no_prerequisites(self) -> None:
        result = WorkflowAssembler().assemble(_ctx())
        assert result.status is AssemblyStatus.COMPLETE
        assert result.profile.state is WorkflowState.READY
        assert result.profile.steps[0].state is WorkflowStepState.READY
        assert len(result.profile.executions) == 1
        execution = result.profile.executions[0]
        assert execution.status is WorkflowStepState.READY
        assert execution.ended_at is None
        assert execution.failure is None
        assert execution.outcome_ref_ids == ()
        assert result.report.audit is not None
        assert result.report.summary.failed_execution_count == 0
        assert any("skeleton" in note.lower() for note in result.report.limitations)

    def test_pending_when_prerequisites_exist(self) -> None:
        steps = (
            _step(step_id="dsp.workflow.step.a"),
            _step(
                step_id="dsp.workflow.step.b",
                prereqs=("dsp.workflow.step.a",),
            ),
        )
        result = WorkflowAssembler().assemble(_ctx(steps=steps, with_refs=False))
        assert result.profile.state is WorkflowState.PENDING
        assert result.profile.steps[0].state is WorkflowStepState.READY
        assert result.profile.steps[1].state is WorkflowStepState.PENDING
        assert len(result.profile.executions) == 2
        assert result.profile.audit is not None
        assert len(result.profile.audit.entries) == 2

    def test_partial_without_created_at(self) -> None:
        identity = WorkflowIdentity(
            workflow_id="dsp.workflow.demo",
            workflow_name="Demo",
            created_at=None,
        )
        ctx = AssemblyContext(
            identity=identity,
            metadata=_metadata(),
            steps=(_step(),),
            created_at=None,
        )
        result = WorkflowAssembler().assemble(ctx)
        assert result.status is AssemblyStatus.PARTIAL
        assert result.profile.executions[0].started_at == "unknown"
        assert result.warnings

    def test_immutable_output(self) -> None:
        result = WorkflowAssembler().assemble(_ctx())
        with pytest.raises(AttributeError):
            result.report.steps = ()  # type: ignore[misc]

    def test_retry_descriptors_preserved(self) -> None:
        result = WorkflowAssembler().assemble(_ctx())
        policy = result.profile.steps[0].retry_policy
        assert policy is not None
        assert policy.max_attempts == 2
        assert policy.backoff_policy is BackoffPolicy.FIXED


class TestAssemblyValidation:
    def test_missing_steps(self) -> None:
        with pytest.raises(WorkflowError, match="at least one WorkflowStep"):
            WorkflowAssembler().assemble(
                AssemblyContext(
                    identity=_identity(),
                    metadata=_metadata(),
                    steps=(),
                )
            )

    def test_duplicate_step_ids(self) -> None:
        step = _step()
        with pytest.raises(WorkflowError, match="duplicate step ids"):
            WorkflowAssembler().assemble(_ctx(steps=(step, step), with_refs=False))

    def test_broken_prerequisite(self) -> None:
        with pytest.raises(WorkflowError, match="broken transitions"):
            WorkflowAssembler().assemble(
                _ctx(
                    steps=(_step(prereqs=("dsp.workflow.step.missing",)),),
                    with_refs=False,
                )
            )

    def test_illegal_initial_step_state(self) -> None:
        with pytest.raises(WorkflowError, match="illegal initial states"):
            WorkflowAssembler().assemble(
                _ctx(
                    steps=(_step(state=WorkflowStepState.RUNNING),),
                    with_refs=False,
                )
            )

    def test_duplicate_references(self) -> None:
        ref = _ref(
            AnalysisReference,
            id_="dsp.workflow.ref.analysis.1",
            report_id="dsp.analysis.report.1",
        )
        ctx = AssemblyContext(
            identity=_identity(),
            metadata=_metadata(),
            steps=(_step(),),
            analysis_refs=(ref, ref),  # type: ignore[arg-type]
        )
        with pytest.raises(WorkflowError, match="duplicate references"):
            WorkflowAssembler().assemble(ctx)

    def test_broken_transition_step_link(self) -> None:
        with pytest.raises(WorkflowError, match="broken transitions"):
            WorkflowAssembler().assemble(
                _ctx(
                    with_refs=False,
                    transitions=(
                        WorkflowTransition(
                            transition_id="dsp.workflow.tx.1",
                            from_state=WorkflowState.PENDING,
                            to_state=WorkflowState.READY,
                            step_id="dsp.workflow.step.missing",
                            from_step_state=WorkflowStepState.PENDING,
                            to_step_state=WorkflowStepState.READY,
                        ),
                    ),
                )
            )

    def test_duplicate_workflow_ids_assemble_many(self) -> None:
        ctx = _ctx(with_refs=False)
        with pytest.raises(WorkflowError, match="duplicate workflow ids"):
            WorkflowAssembler().assemble_many((ctx, ctx))

    def test_assemble_many_distinct(self) -> None:
        results = WorkflowAssembler().assemble_many(
            (
                _ctx(workflow_id="dsp.workflow.a", with_refs=False),
                _ctx(workflow_id="dsp.workflow.b", with_refs=False),
            )
        )
        assert len(results) == 2
        assert results[0].profile.workflow_id == "dsp.workflow.a"
        assert results[1].profile.workflow_id == "dsp.workflow.b"


class TestAssemblerArchitecture:
    def test_assembler_forbids_upstream_imports(self) -> None:
        path = (
            Path(__file__).resolve().parents[1] / "src" / "workflow" / "assembler.py"
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
