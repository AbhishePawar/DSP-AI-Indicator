"""Provider-neutral raw economic-data models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["RawEconomicDataPoint", "RawEconomicSeries"]


@dataclass(frozen=True, slots=True)
class RawEconomicDataPoint:
    """Provider-neutral, unvalidated single economic observation.

    Attributes:
        observation_date: Raw observation date as reported by the
            provider (format varies by provider).
        value: Raw observed value as reported.
    """

    observation_date: Any
    value: Any


@dataclass(frozen=True, slots=True)
class RawEconomicSeries:
    """Provider-neutral, unvalidated macroeconomic data series.

    Attributes:
        provider_id: Identifier of the provider this raw series came
            from.
        indicator_code: Raw indicator code/label as reported by the
            provider (or already mapped to a platform-agnostic code).
        country: Raw country code/label as reported by the provider.
        points: Raw observations in whatever order the provider
            returned them.
        frequency: Optional raw frequency label (e.g. ``"monthly"`` or
            an ``EconomicFrequency``). When omitted, the normalizer
            rejects the series — frequency is required for
            ``contracts.EconomicSeries``.
        indicator_name: Optional human-readable indicator name.
        unit: Optional unit of measure (e.g. ``"percent"``, ``"index"``).
    """

    provider_id: str
    indicator_code: Any
    country: Any
    points: tuple[RawEconomicDataPoint, ...]
    frequency: Any = None
    indicator_name: Any = None
    unit: Any = None

    def __post_init__(self) -> None:
        """Freeze ``points`` into a tuple without validating its content."""
        object.__setattr__(self, "points", tuple(self.points))
