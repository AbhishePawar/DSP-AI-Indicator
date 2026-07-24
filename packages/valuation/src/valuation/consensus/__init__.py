"""Cross-Method Validation & Consensus — public package surface."""

from __future__ import annotations

from valuation.consensus.consensus_engine import ConsensusEngine
from valuation.consensus.consensus_explainability import (
    ConsensusExplainedValue,
    explain_many,
    explain_step,
)
from valuation.consensus.consensus_models import (
    CONSENSUS_VERSION,
    RESEARCH_DISCLAIMER,
    CompanyProfile,
    ConsensusInputs,
    ConsensusQualityFlag,
    ConsensusResult,
    ConsensusValidationError,
    DisagreementAnalysis,
    MethodCategory,
    MethodWeightDetail,
    OutlierReport,
    OutlierThresholds,
    SensitivitySummary,
    StandardizedMethodResult,
    WeightingMode,
    default_category_for_method,
    normalize_method_input,
    to_v2_aggregate_payload,
    to_valuation_result,
)
from valuation.consensus.consensus_validation import validate_consensus_inputs

__all__ = [
    "CONSENSUS_VERSION",
    "RESEARCH_DISCLAIMER",
    "CompanyProfile",
    "ConsensusEngine",
    "ConsensusExplainedValue",
    "ConsensusInputs",
    "ConsensusQualityFlag",
    "ConsensusResult",
    "ConsensusValidationError",
    "DisagreementAnalysis",
    "MethodCategory",
    "MethodWeightDetail",
    "OutlierReport",
    "OutlierThresholds",
    "SensitivitySummary",
    "StandardizedMethodResult",
    "WeightingMode",
    "default_category_for_method",
    "explain_many",
    "explain_step",
    "normalize_method_input",
    "to_v2_aggregate_payload",
    "to_valuation_result",
    "validate_consensus_inputs",
]
