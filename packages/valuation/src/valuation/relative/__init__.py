"""Relative Valuation Suite — public package surface."""

from __future__ import annotations

from valuation.relative.relative_engine import RelativeEngine
from valuation.relative.relative_explainability import (
    RelativeExplainedValue,
    explain_many,
    explain_step,
)
from valuation.relative.relative_models import (
    RELATIVE_VERSION,
    RESEARCH_DISCLAIMER,
    BenchmarkMultiples,
    BenchmarkScope,
    MultipleAnalysis,
    MultipleProvider,
    MultipleSnapshot,
    RelativeInputs,
    RelativeMultiple,
    RelativeQualityFlag,
    RelativeValuationResult,
    StaticMultipleProvider,
    to_v2_aggregate_payload,
    to_valuation_result,
)
from valuation.relative.relative_validation import validate_relative_inputs

__all__ = [
    "RELATIVE_VERSION",
    "RESEARCH_DISCLAIMER",
    "BenchmarkMultiples",
    "BenchmarkScope",
    "MultipleAnalysis",
    "MultipleProvider",
    "MultipleSnapshot",
    "RelativeEngine",
    "RelativeExplainedValue",
    "RelativeInputs",
    "RelativeMultiple",
    "RelativeQualityFlag",
    "RelativeValuationResult",
    "StaticMultipleProvider",
    "explain_many",
    "explain_step",
    "to_v2_aggregate_payload",
    "to_valuation_result",
    "validate_relative_inputs",
]
