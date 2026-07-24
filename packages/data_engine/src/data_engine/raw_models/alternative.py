"""Provider-neutral raw alternative-data models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

__all__ = ["RawAlternativeData"]


@dataclass(frozen=True, slots=True)
class RawAlternativeData:
    """Provider-neutral, unvalidated alternative/behavioral data point.

    Attributes:
        provider_id: Identifier of the provider this raw data came
            from.
        symbol: Raw instrument symbol/ticker as reported by the
            provider.
        signal_name: Raw provider-specific label for the kind of
            signal reported (e.g. ``"social_sentiment"``,
            ``"short_interest"``).
        timestamp: Raw timestamp as reported by the provider.
        value: Raw signal value as reported.
        extra: Additional provider-specific fields kept verbatim.
    """

    provider_id: str
    symbol: str
    signal_name: Any
    timestamp: Any
    value: Any
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Wrap ``extra`` in a read-only view without validating its content."""
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))
