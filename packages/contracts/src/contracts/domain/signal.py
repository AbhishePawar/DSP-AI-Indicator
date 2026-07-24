"""Signal domain contract.

A :class:`Signal` is a directional or quantitative reading about an
instrument produced by any analytical engine (Indicator, Fundamental,
Economic, Valuation, or Behavioral). It is the common shape every
analytical engine emits so that downstream engines (Portfolio
Intelligence, Risk, AI Investment Committee) can consume signals
uniformly, regardless of which engine produced them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts._validation import (
    ensure_in_range,
    ensure_non_empty_str,
    ensure_timezone_aware,
)
from contracts.domain.explanation import Explanation
from contracts.domain.instrument import Instrument
from contracts.enums import EngineSource, SignalDirection


@dataclass(frozen=True, slots=True)
class Signal:
    """Immutable analytical reading about a single instrument.

    Attributes:
        instrument: The instrument this signal describes.
        source_engine: Which platform engine produced this signal.
        name: Canonical identifier for the signal (e.g.
            ``"rsi_14_overbought"``, ``"sentiment_score"``).
        direction: Directional bias expressed by the signal.
        timestamp: Timezone-aware timestamp the signal applies to.
        value: Optional raw numeric value underlying the signal.
        strength: Optional normalized magnitude/confidence in
            ``[0.0, 1.0]``.
        explanation: Optional explanation of why this signal has this
            direction and value.
    """

    instrument: Instrument
    source_engine: EngineSource
    name: str
    direction: SignalDirection
    timestamp: datetime
    value: float | None = None
    strength: float | None = None
    explanation: Explanation | None = None

    def __post_init__(self) -> None:
        """Validate name content, timestamp, and strength bounds.

        Raises:
            ContractValidationError: If ``name`` is empty, ``timestamp``
                is a naive datetime, or ``strength`` is outside
                ``[0.0, 1.0]``.
        """
        name = ensure_non_empty_str(self.name, field_name="name")
        object.__setattr__(self, "name", name)
        ensure_timezone_aware(self.timestamp, field_name="timestamp")

        if self.strength is not None:
            strength = ensure_in_range(
                self.strength, field_name="strength", minimum=0.0, maximum=1.0
            )
            object.__setattr__(self, "strength", strength)
