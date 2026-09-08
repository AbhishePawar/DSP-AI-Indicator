"""Provider-neutral capability status (SIMPLE-14G).

Each capability is independent. One AVAILABLE field must not fill an
UNAVAILABLE required field. DSP packages import this module only for
status types — never a vendor SDK.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

__all__ = [
    "CapabilityName",
    "CapabilityReport",
    "CapabilityStatus",
    "PriceKind",
    "price_kind_from_fields",
]


class CapabilityStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


class CapabilityName(StrEnum):
    IDENTITY = "IDENTITY"
    QUOTE = "QUOTE"
    FINANCIALS = "FINANCIALS"
    HISTORICAL = "HISTORICAL"
    SHARES = "SHARES"
    CORPORATE_ACTIONS = "CORPORATE_ACTIONS"
    RESEARCH = "RESEARCH"


class PriceKind(StrEnum):
    CURRENT = "CURRENT"
    PREVIOUS_CLOSE = "PREVIOUS_CLOSE"
    DELAYED = "DELAYED"
    HISTORICAL = "HISTORICAL"
    INDICATIVE = "INDICATIVE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CapabilityReport:
    """Independent status for one acquisition capability."""

    name: CapabilityName
    status: CapabilityStatus
    detail: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name.value,
            "status": self.status.value,
            "detail": self.detail,
        }


class CapabilityResolver(Protocol):
    def resolve(self) -> Mapping[CapabilityName, CapabilityReport]: ...


def price_kind_from_fields(
    *,
    current_available: bool,
    previous_close_available: bool,
) -> PriceKind:
    """CURRENT and PREVIOUS_CLOSE are distinct. Previous close never becomes current."""
    if current_available:
        return PriceKind.CURRENT
    if previous_close_available:
        return PriceKind.PREVIOUS_CLOSE
    return PriceKind.UNKNOWN
