"""Provider-neutral raw market-data models.

These models capture provider data *after* a provider adapter has mapped
vendor-specific field names onto this shared shape, but *before* any
type coercion or validation has happened. They are not ``contracts``
types and never will be — see the module docstring for
``data_engine.raw_models`` for the full rationale.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

__all__ = ["RawMarketBar", "RawMarketSeries"]


@dataclass(frozen=True, slots=True)
class RawMarketBar:
    """Provider-neutral, unvalidated representation of one price bar.

    Every value field is intentionally loosely typed (``Any``) because
    raw provider data has not yet been coerced, validated, or checked
    for structural integrity — that is the Normalizer's and Validation
    Pipeline's job, not this model's. A ``RawMarketBar`` only asserts
    that *some* value was reported for each attribute; it makes no
    claim about that value's type, range, or plausibility.

    Attributes:
        provider_id: Identifier of the provider this raw bar came from
            (e.g. ``"yahoo_finance"``), used for provenance and for
            attributing errors to the right provider.
        timestamp: Raw timestamp as reported by the provider (could be
            an ISO string, a Unix epoch int/float, an already-parsed
            ``datetime``, etc.).
        open: Raw opening price as reported.
        high: Raw high price as reported.
        low: Raw low price as reported.
        close: Raw closing price as reported.
        volume: Raw traded volume as reported, if any.
        adjusted_close: Raw dividend/split-adjusted close, if reported.
        extra: Any additional provider-specific fields not covered
            above, kept verbatim for forward-compatibility.
    """

    provider_id: str
    timestamp: Any
    open: Any
    high: Any
    low: Any
    close: Any
    volume: Any = None
    adjusted_close: Any = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Wrap ``extra`` in a read-only view without validating its content."""
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))


@dataclass(frozen=True, slots=True)
class RawMarketSeries:
    """Provider-neutral, unvalidated collection of raw price bars.

    No chronological ordering or duplicate-freedom is assumed or
    enforced here — that is the Validation Pipeline's responsibility,
    applied after normalization.

    Attributes:
        provider_id: Identifier of the provider this raw series came
            from.
        symbol: Raw instrument symbol/ticker as reported by the
            provider (not yet resolved against a ``contracts.Instrument``).
        bars: Raw bars in whatever order the provider returned them.
    """

    provider_id: str
    symbol: str
    bars: tuple[RawMarketBar, ...]

    def __post_init__(self) -> None:
        """Freeze ``bars`` into a tuple without validating its content."""
        object.__setattr__(self, "bars", tuple(self.bars))
