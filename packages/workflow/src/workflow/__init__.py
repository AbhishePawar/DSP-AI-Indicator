"""Workflow Intelligence public API (H1.3 — full pipeline through reporter)."""

from __future__ import annotations

from workflow.assembler import AssemblyContext, AssemblyResult, WorkflowAssembler
from workflow.engine import (
    EngineContext,
    EngineResult,
    ExecutionResult,
    StepExecutionResult,
    StepFacadeResult,
    SubsystemFacadePort,
    WorkflowEngine,
)
from workflow.enums import (
    AssemblyStatus,
    BackoffPolicy,
    EngineStatus,
    FailureClass,
    ReportingStatus,
    WorkflowState,
    WorkflowStepState,
)
from workflow.exceptions import WorkflowError
from workflow.models import (
    ExecutionAudit,
    FailureDescriptor,
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
from workflow.reporter import (
    ExecutionSection,
    ReportMetadata,
    ReportingContext,
    ReportingResult,
    WorkflowReporter,
)
from workflow.validation import (
    ALLOWED_STEP_TRANSITIONS,
    ALLOWED_WORKFLOW_TRANSITIONS,
    assert_legal_step_transition,
    assert_legal_workflow_transition,
    assert_unique_workflow_ids,
    require_decimal,
    validate_retry_policy_fields,
)

__all__ = [
    "ALLOWED_STEP_TRANSITIONS",
    "ALLOWED_WORKFLOW_TRANSITIONS",
    "AnalysisReference",
    "AssemblyContext",
    "AssemblyResult",
    "AssemblyStatus",
    "BackoffPolicy",
    "ComparisonReference",
    "DecisionReference",
    "EngineContext",
    "EngineResult",
    "EngineStatus",
    "ExecutionAudit",
    "ExecutionResult",
    "ExecutionSection",
    "FailureClass",
    "FailureDescriptor",
    "IndustryEvidenceReference",
    "PortfolioReference",
    "QuantitativeRiskReference",
    "RecommendationReference",
    "ReportMetadata",
    "ReportingContext",
    "ReportingResult",
    "ReportingStatus",
    "ResearchReference",
    "RetryPolicy",
    "RiskReference",
    "StepExecutionResult",
    "StepFacadeResult",
    "SubsystemFacadePort",
    "WorkflowAssembler",
    "WorkflowEngine",
    "WorkflowError",
    "WorkflowExecution",
    "WorkflowIdentity",
    "WorkflowMetadata",
    "WorkflowProfile",
    "WorkflowReport",
    "WorkflowReporter",
    "WorkflowState",
    "WorkflowStep",
    "WorkflowStepState",
    "WorkflowSummary",
    "WorkflowTransition",
    "assert_legal_step_transition",
    "assert_legal_workflow_transition",
    "assert_unique_workflow_ids",
    "require_decimal",
    "validate_retry_policy_fields",
]

__version__ = "0.4.0"
