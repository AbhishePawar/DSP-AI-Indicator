"""Financial Data Derivation — canonical REPORTED / CALCULATED / UNAVAILABLE layer."""

from __future__ import annotations

from financial.derivation.engine import (
    FinancialDerivationEngine,
    as_reported,
    derive,
)
from financial.derivation.formulas import (
    FORMULA_AVERAGE_EQUITY,
    FORMULA_DEBT_TO_EQUITY,
    FORMULA_EPS_GROWTH,
    FORMULA_FCF,
    FORMULA_GROSS_MARGIN,
    FORMULA_GROSS_MARGIN_FROM_COGS,
    FORMULA_NET_MARGIN,
    FORMULA_OPERATING_MARGIN,
    FORMULA_REVENUE_GROWTH,
    FORMULA_ROCE,
    FORMULA_ROE,
    FORMULA_TOTAL_DEBT,
    FORMULA_WORKING_CAPITAL,
)
from financial.derivation.models import (
    DERIVATION_ENGINE_VERSION,
    DerivationInput,
    DerivedFinancialValue,
    FinancialValueStatus,
    PeriodRule,
)

__all__ = [
    "DERIVATION_ENGINE_VERSION",
    "FORMULA_AVERAGE_EQUITY",
    "FORMULA_DEBT_TO_EQUITY",
    "FORMULA_EPS_GROWTH",
    "FORMULA_FCF",
    "FORMULA_GROSS_MARGIN",
    "FORMULA_GROSS_MARGIN_FROM_COGS",
    "FORMULA_NET_MARGIN",
    "FORMULA_OPERATING_MARGIN",
    "FORMULA_REVENUE_GROWTH",
    "FORMULA_ROCE",
    "FORMULA_ROE",
    "FORMULA_TOTAL_DEBT",
    "FORMULA_WORKING_CAPITAL",
    "DerivationInput",
    "DerivedFinancialValue",
    "FinancialDerivationEngine",
    "FinancialValueStatus",
    "PeriodRule",
    "as_reported",
    "derive",
]
