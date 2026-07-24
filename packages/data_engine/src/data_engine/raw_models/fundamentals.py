"""Provider-neutral raw fundamental-data models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

__all__ = ["RawFundamentalData"]


@dataclass(frozen=True, slots=True)
class RawFundamentalData:
    """Provider-neutral, unvalidated representation of one financial statement.

    Line items are kept as a flat mapping of provider-specific labels to
    raw values rather than named fields, because different providers use
    different label sets (e.g. ``"totalRevenue"`` vs ``"revenue"``) — the
    Normalizer is responsible for mapping these onto
    ``contracts.FundamentalStatement``'s known fields.

    Attributes:
        provider_id: Identifier of the provider this raw statement came
            from.
        symbol: Raw instrument symbol/ticker as reported by the
            provider.
        period_end: Raw reporting period end as reported (format varies
            by provider — could be a string, a ``date``, or a
            ``datetime``).
        period_type: Raw period-type label as reported by the provider
            (e.g. ``"FY"``, ``"Q1"``, ``"annual"`` — not yet mapped onto
            ``contracts.enums.StatementPeriodType``).
        line_items: Raw financial statement line items as reported.
    """

    provider_id: str
    symbol: str
    period_end: Any
    period_type: Any
    line_items: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Wrap ``line_items`` in a read-only view without validating content."""
        object.__setattr__(self, "line_items", MappingProxyType(dict(self.line_items)))
