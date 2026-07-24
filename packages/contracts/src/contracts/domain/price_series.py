"""PriceSeries domain contract.

A :class:`PriceSeries` is an ordered, immutable collection of
:class:`~contracts.domain.price_bar.PriceBar` observations for a single
:class:`~contracts.domain.instrument.Instrument`. It provides only
structural accessors — no returns, moving averages, or other derived
statistics, which are the responsibility of the Indicator Engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from contracts.domain.instrument import Instrument
from contracts.domain.price_bar import PriceBar
from contracts.enums import BarFrequency
from contracts.exceptions import ContractValidationError


@dataclass(frozen=True, slots=True)
class PriceSeries:
    """Immutable, chronologically ordered series of price bars.

    Attributes:
        instrument: The instrument this series describes.
        frequency: Sampling frequency of the bars.
        bars: Chronologically ordered, duplicate-free price bars.
    """

    instrument: Instrument
    frequency: BarFrequency
    bars: tuple[PriceBar, ...]

    def __post_init__(self) -> None:
        """Validate non-emptiness and chronological ordering of bars.

        Raises:
            ContractValidationError: If ``bars`` is empty, not sorted in
                strictly ascending chronological order, or contains
                duplicate timestamps.
        """
        bars = tuple(self.bars)
        if len(bars) == 0:
            msg = "bars must not be empty"
            raise ContractValidationError(msg)

        timestamps = [bar.timestamp for bar in bars]
        if timestamps != sorted(timestamps):
            msg = "bars must be sorted in strictly ascending chronological order"
            raise ContractValidationError(msg)
        if len(set(timestamps)) != len(timestamps):
            msg = "bars must not contain duplicate timestamps"
            raise ContractValidationError(msg)

        object.__setattr__(self, "bars", bars)

    @property
    def length(self) -> int:
        """Return the number of bars in the series."""
        return len(self.bars)

    @property
    def start(self) -> PriceBar:
        """Return the earliest bar in the series."""
        return self.bars[0]

    @property
    def end(self) -> PriceBar:
        """Return the most recent bar in the series."""
        return self.bars[-1]
