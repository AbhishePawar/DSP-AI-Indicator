"""Residual Income Valuation — public package surface."""

from __future__ import annotations

from valuation.residual_income.residual_income_engine import (
    ResidualIncomeEngine,
    verify_clean_surplus,
)
from valuation.residual_income.residual_income_explainability import RiExplainedValue
from valuation.residual_income.residual_income_models import (
    RESEARCH_DISCLAIMER,
    RESIDUAL_INCOME_VERSION,
    CleanSurplusCheck,
    ResidualIncomeInputs,
    ResidualIncomeResult,
    ResidualIncomeScenario,
    ResidualIncomeYear,
    RiConfidenceDetail,
    RiQualityFlag,
    RiScenarioResult,
    RiSensitivityCell,
    RiSensitivityMatrix,
    RiValidationSummary,
    RoeForecastModel,
    to_v2_aggregate_payload,
)
from valuation.residual_income.residual_income_validation import (
    validate_residual_income_inputs,
)

__all__ = [
    "RESEARCH_DISCLAIMER",
    "RESIDUAL_INCOME_VERSION",
    "CleanSurplusCheck",
    "ResidualIncomeEngine",
    "ResidualIncomeInputs",
    "ResidualIncomeResult",
    "ResidualIncomeScenario",
    "ResidualIncomeYear",
    "RiConfidenceDetail",
    "RiExplainedValue",
    "RiQualityFlag",
    "RiScenarioResult",
    "RiSensitivityCell",
    "RiSensitivityMatrix",
    "RiValidationSummary",
    "RoeForecastModel",
    "to_v2_aggregate_payload",
    "validate_residual_income_inputs",
    "verify_clean_surplus",
]
