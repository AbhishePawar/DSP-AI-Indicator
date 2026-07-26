"""Version and provenance metadata for Economic Moat Intelligence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from economic_moat.exceptions import EconomicMoatValidationError

__all__ = [
    "ECONOMIC_MOAT_VERSION",
    "FRAMEWORK_VERSION",
    "EconomicMetadata",
]

ECONOMIC_MOAT_VERSION = "0.2.0-economic-moat"
FRAMEWORK_VERSION = "0.2.0-core"


@dataclass(frozen=True, slots=True)
class EconomicMetadata:
    """Immutable provenance for an Economic Moat analysis artifact."""

    engine_version: str
    framework_version: str = FRAMEWORK_VERSION
    company: str = ""
    ticker: str = ""
    input_types: tuple[str, ...] = (
        "FinancialAnalysis",
        "BusinessQualityAnalysis",
    )
    schema_version: str = "2"

    def __post_init__(self) -> None:
        engine_version = self.engine_version.strip()
        framework_version = self.framework_version.strip()
        schema_version = self.schema_version.strip()
        if not engine_version:
            raise EconomicMoatValidationError("metadata.engine_version is required")
        if not framework_version:
            raise EconomicMoatValidationError("metadata.framework_version is required")
        if not schema_version:
            raise EconomicMoatValidationError("metadata.schema_version is required")
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
