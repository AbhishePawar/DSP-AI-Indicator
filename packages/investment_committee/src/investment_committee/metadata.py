"""Version and provenance metadata for Investment Committee."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from investment_committee.exceptions import InvestmentCommitteeValidationError

__all__ = [
    "COMMITTEE_VERSION",
    "FRAMEWORK_VERSION",
    "InvestmentCommitteeMetadata",
]

COMMITTEE_VERSION = "0.1.0-investment-committee"
FRAMEWORK_VERSION = "0.1.0-core"


@dataclass(frozen=True, slots=True)
class InvestmentCommitteeMetadata:
    engine_version: str
    framework_version: str = FRAMEWORK_VERSION
    company: str = ""
    ticker: str = ""
    input_types: tuple[str, ...] = (
        "InvestmentRecommendation",
        "BusinessQualityAggregation",
        "EconomicAnalysis",
        "ManagementAnalysis",
        "FinancialStrengthAnalysis",
        "EarningsQualityAnalysis",
        "GrowthQualityAnalysis",
        "OverallValuationResult|ValuationSignals",
    )
    schema_version: str = "1"

    def __post_init__(self) -> None:
        engine_version = self.engine_version.strip()
        framework_version = self.framework_version.strip()
        schema_version = self.schema_version.strip()
        if not engine_version:
            raise InvestmentCommitteeValidationError(
                "metadata.engine_version is required"
            )
        if not framework_version:
            raise InvestmentCommitteeValidationError(
                "metadata.framework_version is required"
            )
        if not schema_version:
            raise InvestmentCommitteeValidationError(
                "metadata.schema_version is required"
            )
        object.__setattr__(self, "engine_version", engine_version)
        object.__setattr__(self, "framework_version", framework_version)
        object.__setattr__(self, "company", self.company.strip())
        object.__setattr__(self, "ticker", self.ticker.strip().upper())
        object.__setattr__(self, "input_types", tuple(self.input_types))
        object.__setattr__(self, "schema_version", schema_version)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "framework_version": self.framework_version,
            "company": self.company,
            "ticker": self.ticker,
            "input_types": list(self.input_types),
            "schema_version": self.schema_version,
        }
