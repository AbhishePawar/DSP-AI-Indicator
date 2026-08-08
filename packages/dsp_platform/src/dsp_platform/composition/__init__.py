"""EPIC-001 platform composition — orchestration only (no domain scoring)."""

from __future__ import annotations

from dsp_platform.composition.adapters import (
    CompositionInputError,
    build_composition_request,
    composition_capability_manifest,
    composition_package_versions,
    pipeline_result_public_dict,
)
from dsp_platform.composition.authenticated_valuation import (
    DATA_UNAVAILABLE,
    AuthenticatedValuationBundle,
    AuthenticatedValuationError,
    load_authenticated_valuation_bundle,
    signals_from_assessment,
)
from dsp_platform.composition.config import PipelineConfiguration
from dsp_platform.composition.context import ExecutionContext
from dsp_platform.composition.errors import CompositionStageError
from dsp_platform.composition.models import (
    CompositionRequest,
    ExecutionMetadata,
    ExecutionTraceEntry,
    PipelineResult,
    StageOutcome,
    StageStatus,
)
from dsp_platform.composition.orchestrator import PlatformOrchestrator
from dsp_platform.composition.pipeline import (
    EXECUTION_ORDER,
    PipelineStage,
    run_execution_pipeline,
)
from dsp_platform.composition.resolver import DependencyResolver
from dsp_platform.composition.risk_view import CompanyRiskView, RiskCategoryView
from dsp_platform.composition.versions import COMPOSITION_PIPELINE_VERSION

__all__ = [
    "COMPOSITION_PIPELINE_VERSION",
    "DATA_UNAVAILABLE",
    "EXECUTION_ORDER",
    "AuthenticatedValuationBundle",
    "AuthenticatedValuationError",
    "CompanyRiskView",
    "CompositionInputError",
    "CompositionRequest",
    "CompositionStageError",
    "DependencyResolver",
    "ExecutionContext",
    "ExecutionMetadata",
    "ExecutionTraceEntry",
    "PipelineConfiguration",
    "PipelineResult",
    "PipelineStage",
    "PlatformOrchestrator",
    "RiskCategoryView",
    "StageOutcome",
    "StageStatus",
    "build_composition_request",
    "composition_capability_manifest",
    "composition_package_versions",
    "load_authenticated_valuation_bundle",
    "pipeline_result_public_dict",
    "run_execution_pipeline",
    "signals_from_assessment",
]
