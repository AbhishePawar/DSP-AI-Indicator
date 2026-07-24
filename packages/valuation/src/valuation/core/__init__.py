"""Valuation Core Framework — public surface.

Reusable infrastructure for all future valuation methods.
Does not implement a valuation methodology.
"""

from __future__ import annotations

from valuation.core.confidence_engine import ConfidenceDetail, ConfidenceEngine
from valuation.core.errors import (
    ConvergenceError,
    ExplainabilityError,
    ForecastError,
    MetadataError,
    ScenarioError,
    SensitivityError,
    ValidationError,
    ValuationError,
)
from valuation.core.explainability_engine import ExplainabilityEngine
from valuation.core.interfaces import (
    ConfidenceProvider,
    ExplainabilityProvider,
    ScenarioProvider,
    SensitivityProvider,
    ValidationProvider,
    ValuationMethod,
)
from valuation.core.metadata import RESEARCH_DISCLAIMER, VALUATION_CORE_VERSION
from valuation.core.quality_flags import QualityFlag
from valuation.core.result_models import (
    ExplainabilityRecord,
    ScenarioKind,
    ScenarioOutcome,
    SensitivityCell,
    SensitivityMatrix,
    ValidationSummary,
    ValuationMetadata,
    ValuationResult,
)
from valuation.core.scenario_engine import ScenarioEngine, ScenarioSpec
from valuation.core.sensitivity_engine import SensitivityAxis, SensitivityEngine
from valuation.core.validation_engine import ValidationEngine

__all__ = [
    "VALUATION_CORE_VERSION",
    "RESEARCH_DISCLAIMER",
    "ConfidenceDetail",
    "ConfidenceEngine",
    "ConfidenceProvider",
    "ConvergenceError",
    "ExplainabilityEngine",
    "ExplainabilityError",
    "ExplainabilityProvider",
    "ExplainabilityRecord",
    "ForecastError",
    "MetadataError",
    "QualityFlag",
    "ScenarioEngine",
    "ScenarioError",
    "ScenarioKind",
    "ScenarioOutcome",
    "ScenarioProvider",
    "ScenarioSpec",
    "SensitivityAxis",
    "SensitivityCell",
    "SensitivityEngine",
    "SensitivityError",
    "SensitivityMatrix",
    "SensitivityProvider",
    "ValidationEngine",
    "ValidationError",
    "ValidationProvider",
    "ValidationSummary",
    "ValuationError",
    "ValuationMetadata",
    "ValuationMethod",
    "ValuationResult",
]
