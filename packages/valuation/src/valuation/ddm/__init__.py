"""Dividend Discount Model (DDM) — public package surface."""

from __future__ import annotations

from valuation.ddm.ddm_engine import DdmEngine
from valuation.ddm.ddm_explainability import DdmExplainedValue, explain_many, explain_step
from valuation.ddm.ddm_models import (
    DDM_VERSION,
    RESEARCH_DISCLAIMER,
    DdmInputs,
    DdmMethod,
    DdmQualityFlag,
    DdmResult,
    DividendQuality,
    DividendYear,
    to_v2_aggregate_payload,
    to_valuation_result,
)
from valuation.ddm.ddm_validation import validate_ddm_inputs

__all__ = [
    "DDM_VERSION",
    "RESEARCH_DISCLAIMER",
    "DdmEngine",
    "DdmExplainedValue",
    "DdmInputs",
    "DdmMethod",
    "DdmQualityFlag",
    "DdmResult",
    "DividendQuality",
    "DividendYear",
    "explain_many",
    "explain_step",
    "to_v2_aggregate_payload",
    "to_valuation_result",
    "validate_ddm_inputs",
]
