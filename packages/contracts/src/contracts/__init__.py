"""Contracts package public API.

Contracts is the Shared Kernel of the DSP AI Indicator platform. It defines
the domain models and explainability primitives every engine uses to
communicate, and depends on nothing beyond the Python standard library.

See ``packages/contracts/README.md`` and
``docs/DSP_AI_INDICATOR_ARCHITECTURE.md`` for the platform-wide usage and
dependency rules that govern this package.
"""

from contracts.domain import (
    EconomicContext,
    EconomicDataPoint,
    EconomicSeries,
    Evidence,
    Explanation,
    FundamentalContext,
    FundamentalStatement,
    Instrument,
    MARKET_CAPITALIZATION_KEY,
    MarginOfSafety,
    PriceBar,
    PriceSeries,
    Recommendation,
    Signal,
    TechnicalContext,
    ValuationContext,
    ValuationSummary,
)
from contracts.enums import (
    AnalyticalStance,
    AssetClass,
    BarFrequency,
    EconomicFrequency,
    EngineSource,
    RecommendationAction,
    SignalDirection,
    StatementPeriodType,
    ValuationConfidence,
)
from contracts.exceptions import ContractError, ContractValidationError

__all__ = [
    "AnalyticalStance",
    "AssetClass",
    "BarFrequency",
    "ContractError",
    "ContractValidationError",
    "EconomicContext",
    "EconomicDataPoint",
    "EconomicFrequency",
    "EconomicSeries",
    "EngineSource",
    "Evidence",
    "Explanation",
    "FundamentalContext",
    "FundamentalStatement",
    "Instrument",
    "MARKET_CAPITALIZATION_KEY",
    "MarginOfSafety",
    "PriceBar",
    "PriceSeries",
    "Recommendation",
    "RecommendationAction",
    "Signal",
    "SignalDirection",
    "StatementPeriodType",
    "TechnicalContext",
    "ValuationConfidence",
    "ValuationContext",
    "ValuationSummary",
]

__version__ = "0.3.0"
