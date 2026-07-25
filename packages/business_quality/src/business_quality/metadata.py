"""Framework metadata for Business Quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "BUSINESS_QUALITY_VERSION",
    "FRAMEWORK_VERSION",
    "BusinessQualityMetadata",
]

BUSINESS_QUALITY_VERSION = "0.7.0-business-quality"
FRAMEWORK_VERSION = "0.1.0-framework"


@dataclass(frozen=True, slots=True)
class BusinessQualityMetadata:
    """Provenance metadata for a Business Quality analysis artifact."""

    engine_version: str
    framework_version: str = FRAMEWORK_VERSION
    company: str = ""
    ticker: str = ""
    modules_composed: tuple[str, ...] = ()
    schema_version: str = "1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_version": self.engine_version,
            "framework_version": self.framework_version,
            "company": self.company,
            "ticker": self.ticker,
            "modules_composed": list(self.modules_composed),
            "schema_version": self.schema_version,
        }
