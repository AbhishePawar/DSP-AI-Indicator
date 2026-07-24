"""Workflow domain model tests (H1.0)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from core.exceptions import ValidationError

from workflow import (
    AnalysisReference,
    BackoffPolicy,
    ComparisonReference,
    DecisionReference,
    ExecutionAudit,
    FailureClass,
    FailureDescriptor,
    IndustryEvidenceReference,
    PortfolioReference,
    QuantitativeRiskReference,
    RecommendationReference,
    ResearchReference,
    RetryPolicy,
    RiskReference,
    WorkflowError,
    WorkflowExecution,
    WorkflowIdentity,
    WorkflowMetadata,
    WorkflowProfile,
    WorkflowReport,
    WorkflowState,
    WorkflowStep,
    WorkflowStepState,
    WorkflowSummary,
    WorkflowTransition,
    assert_legal_step_transition,
    assert_legal_workflow_transition,
    assert_unique_workflow_ids,
)


def _identity() -> WorkflowIdentity:
    return WorkflowIdentity(
        workflow_id="dsp.workflow.demo",
        workflow_name="Demo Workflow",
        created_at="2026-07-21T00:00:00Z",
    )


def _metadata() -> WorkflowMetadata:
    return WorkflowMetadata(
        playbook_id="dsp.workflow.playbook.demo",
        as_of="2026-07-21",
        owner="platform",
        tags=("investigation",),
    )


def _ref(
    cls: type,
    *,
    id_: str = "dsp.workflow.ref.analysis.1",
    report_id: str = "dsp.analysis.report.1",
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
) -> WorkflowStep:
    return WorkflowStep(
        step_id=step_id,
        step_name="Run analysis",
        capability="analysis",
        prerequisite_step_ids=prereqs,
        retry_policy=RetryPolicy(
            max_attempts=2,
            backoff_policy=BackoffPolicy.FIXED,
            backoff_base_ms=Decimal("100"),
            retryable_failure_classes=(FailureClass.TIMEOUT,),
        ),
    )


def _execution(
    *,
    execution_id: str = "dsp.workflow.exec.1",
    step_id: str = "dsp.workflow.step.analysis",
    status: WorkflowStepState = WorkflowStepState.SUCCEEDED,
    outcome_ref_ids: tuple[str, ...] = (),
    failure: FailureDescriptor | None = None,
) -> WorkflowExecution:
    return WorkflowExecution(
        execution_id=execution_id,
        step_id=step_id,
        attempt=1,
        status=status,
        started_at="2026-07-21T12:00:00Z",
        ended_at="2026-07-21T12:01:00Z",
        outcome_ref_ids=outcome_ref_ids,
        failure=failure,
        provenance=("adapter:demo",),
    )


class TestConstruction:
    def test_profile_and_report(self) -> None:
        analysis = _ref(AnalysisReference)
        decision = _ref(
            DecisionReference,
            id_="dsp.workflow.ref.decision.1",
            report_id="dsp.decision.report.1",
        )
        step = _step()
        transition = WorkflowTransition(
            transition_id="dsp.workflow.tx.pending_ready",
            from_state=WorkflowState.PENDING,
            to_state=WorkflowState.READY,
        )
        execution = _execution(outcome_ref_ids=(analysis.id,))
        profile = WorkflowProfile(
            identity=_identity(),
            state=WorkflowState.READY,
            metadata=_metadata(),
            steps=(step,),
            transitions=(transition,),
            executions=(execution,),
            audit=ExecutionAudit(entries=(execution,)),
            summary=WorkflowSummary(step_count=1, execution_count=1),
            analysis_refs=(analysis,),  # type: ignore[arg-type]
            decision_refs=(decision,),  # type: ignore[arg-type]
            industry_evidence_refs=(
                _ref(
                    IndustryEvidenceReference,
                    id_="dsp.workflow.ref.ief.1",
                    report_id="dsp.ief.report.1",
                ),  # type: ignore[arg-type]
            ),
            comparison_refs=(
                _ref(
                    ComparisonReference,
                    id_="dsp.workflow.ref.comparison.1",
                    report_id="dsp.comparison.report.1",
                ),  # type: ignore[arg-type]
            ),
            portfolio_refs=(
                _ref(
                    PortfolioReference,
                    id_="dsp.workflow.ref.portfolio.1",
                    report_id="dsp.portfolio.report.1",
                ),  # type: ignore[arg-type]
            ),
            risk_refs=(
                _ref(
                    RiskReference,
                    id_="dsp.workflow.ref.risk.1",
                    report_id="dsp.risk.report.1",
                ),  # type: ignore[arg-type]
            ),
            research_refs=(
                _ref(
                    ResearchReference,
                    id_="dsp.workflow.ref.research.1",
                    report_id="dsp.research.report.1",
                ),  # type: ignore[arg-type]
            ),
            quantitative_risk_refs=(
                _ref(
                    QuantitativeRiskReference,
                    id_="dsp.workflow.ref.qrisk.1",
                    report_id="dsp.qrisk.report.1",
                ),  # type: ignore[arg-type]
            ),
            recommendation_refs=(
                _ref(
                    RecommendationReference,
                    id_="dsp.workflow.ref.recommendation.1",
                    report_id="dsp.recommendation.report.1",
                ),  # type: ignore[arg-type]
            ),
        )
        assert profile.workflow_id == "dsp.workflow.demo"

        report = WorkflowReport(
            workflow_id="dsp.workflow.demo",
            state=WorkflowState.READY,
            summary=WorkflowSummary(step_count=1, execution_count=1),
            metadata=_metadata(),
            as_of="2026-07-21",
            steps=(step,),
            transitions=(transition,),
            executions=(execution,),
            analysis_refs=(analysis,),  # type: ignore[arg-type]
            limitations=("Contracts only — no engine.",),
        )
        assert report.workflow_id == "dsp.workflow.demo"
        with pytest.raises(AttributeError):
            report.steps = ()  # type: ignore[misc]


class TestValidation:
    def test_duplicate_workflow_ids(self) -> None:
        assert_unique_workflow_ids(("a", "b"))
        with pytest.raises(WorkflowError, match="duplicate workflow ids"):
            assert_unique_workflow_ids(("dsp.workflow.a", "DSP.WORKFLOW.A"))

    def test_duplicate_step_ids(self) -> None:
        step = _step()
        with pytest.raises(WorkflowError, match="duplicate step ids"):
            WorkflowProfile(
                identity=_identity(),
                state=WorkflowState.PENDING,
                metadata=_metadata(),
                steps=(step, step),
            )

    def test_duplicate_execution_ids(self) -> None:
        step = _step()
        execution = _execution()
        with pytest.raises(WorkflowError, match="duplicate execution ids"):
            WorkflowProfile(
                identity=_identity(),
                state=WorkflowState.PENDING,
                metadata=_metadata(),
                steps=(step,),
                executions=(execution, execution),
            )

    def test_broken_prerequisite(self) -> None:
        with pytest.raises(WorkflowError, match="broken transitions"):
            WorkflowProfile(
                identity=_identity(),
                state=WorkflowState.PENDING,
                metadata=_metadata(),
                steps=(_step(prereqs=("dsp.workflow.step.missing",)),),
            )

    def test_illegal_state_transitions(self) -> None:
        with pytest.raises(WorkflowError, match="illegal state transitions"):
            assert_legal_workflow_transition(
                WorkflowState.COMPLETED, WorkflowState.RUNNING
            )
        with pytest.raises(WorkflowError, match="illegal state transitions"):
            assert_legal_step_transition(
                WorkflowStepState.SUCCEEDED, WorkflowStepState.RUNNING
            )
        with pytest.raises(WorkflowError, match="illegal state transitions"):
            WorkflowTransition(
                transition_id="dsp.workflow.tx.bad",
                from_state=WorkflowState.COMPLETED,
                to_state=WorkflowState.PENDING,
            )

    def test_broken_outcome_reference(self) -> None:
        step = _step()
        with pytest.raises(WorkflowError, match="broken references"):
            WorkflowProfile(
                identity=_identity(),
                state=WorkflowState.PENDING,
                metadata=_metadata(),
                steps=(step,),
                executions=(
                    _execution(outcome_ref_ids=("dsp.workflow.ref.missing",)),
                ),
            )

    def test_duplicate_report_references(self) -> None:
        analysis = _ref(AnalysisReference)
        duplicate = _ref(
            AnalysisReference,
            id_="dsp.workflow.ref.analysis.2",
            report_id="dsp.analysis.report.1",
        )
        with pytest.raises(WorkflowError, match="duplicate report references"):
            WorkflowProfile(
                identity=_identity(),
                state=WorkflowState.PENDING,
                metadata=_metadata(),
                analysis_refs=(analysis, duplicate),  # type: ignore[arg-type]
            )

    def test_invalid_retry_configuration(self) -> None:
        with pytest.raises(WorkflowError, match="invalid retry configuration"):
            RetryPolicy(
                max_attempts=1,
                backoff_policy=BackoffPolicy.EXPONENTIAL,
                backoff_base_ms=None,
            )
        with pytest.raises(WorkflowError, match="invalid retry configuration"):
            RetryPolicy(
                max_attempts=1,
                backoff_policy=BackoffPolicy.NONE,
                backoff_base_ms=Decimal("10"),
            )

    def test_negative_retry_counts(self) -> None:
        with pytest.raises(WorkflowError, match="negative retry counts"):
            RetryPolicy(max_attempts=0)
        with pytest.raises(WorkflowError, match="negative retry counts"):
            WorkflowExecution(
                execution_id="dsp.workflow.exec.x",
                step_id="dsp.workflow.step.analysis",
                attempt=0,
                status=WorkflowStepState.PENDING,
                started_at="2026-07-21T00:00:00Z",
                provenance=("p",),
            )

    def test_missing_provenance(self) -> None:
        with pytest.raises(WorkflowError, match="missing provenance"):
            FailureDescriptor(
                failure_class=FailureClass.TIMEOUT,
                message="timed out",
                provenance=(),
            )
        with pytest.raises(WorkflowError, match="missing provenance"):
            WorkflowExecution(
                execution_id="dsp.workflow.exec.x",
                step_id="dsp.workflow.step.analysis",
                attempt=1,
                status=WorkflowStepState.SUCCEEDED,
                started_at="2026-07-21T00:00:00Z",
                provenance=(),
            )

    def test_decimal_policy_rejects_float(self) -> None:
        with pytest.raises(ValidationError, match="decimal.Decimal"):
            RetryPolicy(
                max_attempts=2,
                backoff_policy=BackoffPolicy.FIXED,
                backoff_base_ms=100.0,  # type: ignore[arg-type]
            )

    def test_broken_reference_digest(self) -> None:
        with pytest.raises(ValidationError, match="broken references"):
            AnalysisReference(
                id="dsp.workflow.ref.x",
                report_id="dsp.analysis.report.x",
                version="1",
                digest="short",
                status="complete",
                generated_at="2026-07-21T00:00:00Z",
            )
