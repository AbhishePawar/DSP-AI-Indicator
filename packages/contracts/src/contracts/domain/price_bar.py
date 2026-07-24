"""PriceBar domain contract.

A :class:`PriceBar` represents a single OHLCV observation for an instrument
over one time interval (e.g. one trading day, one 1-minute bar). It carries
no derived or computed fields — returns, volatility, and similar measures
are the responsibility of the Indicator Engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts._validation import ensure_finite, ensure_timezone_aware
from contracts.exceptions import ContractValidationError


@dataclass(frozen=True, slots=True)
class PriceBar:
    """Immutable OHLCV observation for a single time interval.

    Attributes:
        timestamp: Timezone-aware timestamp marking the interval
            (convention — start vs. close — is defined by the data provider
            that produced it; the contract only requires it be unambiguous
            and timezone-aware).
        open: Opening price of the interval.
        high: Highest traded price during the interval.
        low: Lowest traded price during the interval.
        close: Closing price of the interval.
        volume: Traded volume during the interval.
        adjusted_close: Optional close price adjusted for dividends and
            splits, as supplied by the data provider.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None

    def __post_init__(self) -> None:
        """Validate structural OHLCV integrity.

        Raises:
            ContractValidationError: If the timestamp is naive, any price
                field is non-finite or negative, ``low`` exceeds ``high``,
                ``open``/``close`` fall outside ``[low, high]``, or
                ``volume`` is negative.
        """
        ensure_timezone_aware(self.timestamp, field_name="timestamp")

        open_ = ensure_finite(self.open, field_name="open")
        high = ensure_finite(self.high, field_name="high")
        low = ensure_finite(self.low, field_name="low")
        close = ensure_finite(self.close, field_name="close")
        volume = ensure_finite(self.volume, field_name="volume")

        if any(price < 0 for price in (open_, high, low, close)):
            msg = "open, high, low, and close must be non-negative"
            raise ContractValidationError(msg)
        if low > high:
            msg = f"low ({low}) must not exceed high ({high})"
            raise ContractValidationError(msg)
        if not low <= open_ <= high:
            msg = f"open ({open_}) must fall within [low, high] = [{low}, {high}]"
            raise ContractValidationError(msg)
        if not low <= close <= high:
            msg = f"close ({close}) must fall within [low, high] = [{low}, {high}]"
            raise ContractValidationError(msg)
        if volume < 0:
            msg = f"volume must be non-negative, got {volume}"
            raise ContractValidationError(msg)

        object.__setattr__(self, "open", open_)
        object.__setattr__(self, "high", high)
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "close", close)
        object.__setattr__(self, "volume", volume)

        if self.adjusted_close is not None:
            adjusted_close = ensure_finite(
                self.adjusted_close, field_name="adjusted_close"
            )
            if adjusted_close < 0:
                msg = f"adjusted_close must be non-negative, got {adjusted_close}"
                raise ContractValidationError(msg)
            object.__setattr__(self, "adjusted_close", adjusted_close)
