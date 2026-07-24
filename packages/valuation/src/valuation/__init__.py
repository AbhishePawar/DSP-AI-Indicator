"""Valuation Engine public API.

Additive engines:
* :meth:`ValuationEngine.analyze_dcf` — V1.2 DCF Intelligence
* :meth:`ValuationEngine.analyze_reverse_dcf` — V1.3 Reverse DCF
* :meth:`ValuationEngine.analyze_residual_income` — V1.4 Residual Income
* :mod:`valuation.core` — V1.5 Valuation Core Framework (infrastructure)
* :meth:`ValuationEngine.analyze_epv` — V1.6 Earnings Power Value
* :meth:`ValuationEngine.analyze_graham` — V1.7 Graham Intrinsic Value
"""

from contracts.domain.margin_of_safety import MarginOfSafety
from valuation.assumptions import ValuationAssumptions
from valuation.core import (
    VALUATION_CORE_VERSION,
    ConfidenceEngine,
    ExplainabilityEngine,
    QualityFlag,
    ScenarioEngine,
    SensitivityEngine,
    ValidationEngine,
    ValuationMetadata,
    ValuationResult,
)
from valuation.dcf_intelligence import (
    CapmInputs,
    CapitalStructure,
    CostOfDebtInputs,
    DCF_INTELLIGENCE_VERSION,
    DcfAnalysisInputs,
    DcfBridgeInputs,
    DcfForecastAssumptions,
    DcfMarketInputs,
    DcfMosClassification,
    DcfSensitivitySpec,
    DcfTerminalAssumptions,
    DiscountedCashFlowEngine,
    DiscountedCashFlowResult,
    ExplainedValue,
    HistoricalFcfPoint,
)
from valuation.engine import ValuationEngine
from valuation.enums import ValuationConfidence, ValuationMethod
from valuation.epv import (
    EPV_VERSION,
    EpvEngine,
    EpvInputs,
    EpvQualityFlag,
    EpvResult,
    NormalizationMethod,
    to_valuation_result as to_epv_valuation_result,
    to_v2_aggregate_payload as to_epv_v2_aggregate_payload,
    validate_epv_inputs,
)
from valuation.exceptions import ValuationError
from valuation.graham import (
    GRAHAM_VERSION,
    GrahamEngine,
    GrahamFormula,
    GrahamInputs,
    GrahamQualityFlag,
    GrahamResult,
    to_valuation_result as to_graham_valuation_result,
    to_v2_aggregate_payload as to_graham_v2_aggregate_payload,
    validate_graham_inputs,
)
from valuation.models import (
    IntrinsicValueEstimate,
    MarketSnapshot,
    ValuationAssessment,
    ValuationEvidence,
    ValuationRange,
)
from valuation.residual_income import (
    RESIDUAL_INCOME_VERSION,
    RESEARCH_DISCLAIMER,
    ResidualIncomeEngine,
    ResidualIncomeInputs,
    ResidualIncomeResult,
    ResidualIncomeScenario,
    RiQualityFlag,
    RoeForecastModel,
    to_v2_aggregate_payload,
    validate_residual_income_inputs,
    verify_clean_surplus,
    RiExplainedValue,
)
from valuation.reverse_dcf import (
    REVERSE_DCF_VERSION,
    ReverseDcfEngine,
    ReverseDcfInputs,
    ReverseDcfResult,
    ReverseDcfScenario,
    ReverseExplainedValue,
    validate_reverse_dcf_inputs,
)

__all__ = [
    "CapmInputs",
    "CapitalStructure",
    "ConfidenceEngine",
    "CostOfDebtInputs",
    "DCF_INTELLIGENCE_VERSION",
    "DcfAnalysisInputs",
    "DcfBridgeInputs",
    "DcfForecastAssumptions",
    "DcfMarketInputs",
    "DcfMosClassification",
    "DcfSensitivitySpec",
    "DcfTerminalAssumptions",
    "DiscountedCashFlowEngine",
    "DiscountedCashFlowResult",
    "EPV_VERSION",
    "EpvEngine",
    "EpvInputs",
    "EpvQualityFlag",
    "EpvResult",
    "ExplainabilityEngine",
    "ExplainedValue",
    "GRAHAM_VERSION",
    "GrahamEngine",
    "GrahamFormula",
    "GrahamInputs",
    "GrahamQualityFlag",
    "GrahamResult",
    "HistoricalFcfPoint",
    "IntrinsicValueEstimate",
    "MarginOfSafety",
    "MarketSnapshot",
    "NormalizationMethod",
    "QualityFlag",
    "RESIDUAL_INCOME_VERSION",
    "RESEARCH_DISCLAIMER",
    "REVERSE_DCF_VERSION",
    "ResidualIncomeEngine",
    "ResidualIncomeInputs",
    "ResidualIncomeResult",
    "ResidualIncomeScenario",
    "ReverseDcfEngine",
    "ReverseDcfInputs",
    "ReverseDcfResult",
    "ReverseDcfScenario",
    "ReverseExplainedValue",
    "RiExplainedValue",
    "RiQualityFlag",
    "RoeForecastModel",
    "ScenarioEngine",
    "SensitivityEngine",
    "VALUATION_CORE_VERSION",
    "ValidationEngine",
    "ValuationAssessment",
    "ValuationAssumptions",
    "ValuationConfidence",
    "ValuationEngine",
    "ValuationError",
    "ValuationEvidence",
    "ValuationMetadata",
    "ValuationMethod",
    "ValuationRange",
    "ValuationResult",
    "to_epv_v2_aggregate_payload",
    "to_epv_valuation_result",
    "to_graham_v2_aggregate_payload",
    "to_graham_valuation_result",
    "to_v2_aggregate_payload",
    "validate_epv_inputs",
    "validate_graham_inputs",
    "validate_residual_income_inputs",
    "validate_reverse_dcf_inputs",
    "verify_clean_surplus",
]

__version__ = "0.7.0"
