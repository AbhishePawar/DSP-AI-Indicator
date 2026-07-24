"""Internal orchestration models for the Indicator Engine.

Neither :class:`IndicatorSpec` nor :class:`IndicatorResult` is a
``contracts`` type. They exist purely to carry data between
:class:`~dsp.engine.service.IndicatorEngine` and the signal-generation
components in :mod:`dsp.signals`; other engines must never import them
directly, and they may change shape without being treated as a breaking
change to the platform's shared vocabulary. The only stable, cross-engine
output of this package is the ``contracts.Signal`` /
``contracts.Explanation`` / ``contracts.Evidence`` triple produced by
:meth:`~dsp.engine.service.IndicatorEngine.analyze`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts.domain.instrument import Instrument
from contracts.enums import BarFrequency
from core.exceptions import ValidationError
from core.validation import validate_period


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    """A request to run one registered indicator with one configuration.

    Attributes:
        name: Canonical indicator identifier understood by
            :func:`dsp.registry.get` (e.g. ``"rsi"``). Normalized to
            lowercase.
        period: Lookback window size passed to the indicator.
    """

    name: str
    period: int

    def __post_init__(self) -> None:
        """Normalize the indicator name and validate the period.

        Raises:
            ValidationError: If ``name`` is empty or ``period`` is not a
                positive integer.
        """
        name = self.name.strip().lower()
        if not name:
            msg = "name must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "period", validate_period(self.period))


@dataclass(frozen=True, slots=True)
class IndicatorResult:
    """The outcome of running one :class:`IndicatorSpec` against one series.

    ``source_values`` and ``values`` are plain ``tuple[float, ...]``, not
    NumPy arrays — the boundary between the existing NumPy-based
    :class:`dsp.indicators.base.Indicator` implementations and everything
    downstream of :class:`~dsp.engine.service.IndicatorEngine` is crossed
    exactly once, immediately after ``Indicator.compute()`` returns.

    Attributes:
        instrument: The instrument the series describes.
        name: Canonical indicator identifier (matches ``Indicator.name``).
        period: Lookback window size used for this computation.
        frequency: Sampling frequency of the source price series.
        source_values: Close prices the indicator was computed from,
            aligned index-for-index with ``values``.
        values: Computed indicator output, aligned with ``source_values``.
            Warmup entries are ``float("nan")``, matching the existing
            indicator contract.
        latest_value: The most recent entry in ``values`` (may be
            ``float("nan")`` if the series is shorter than the warmup
            window).
        as_of: Timestamp of the most recent bar in the source series.
        computed_at: Timezone-aware timestamp of when this computation
            ran — execution metadata, not part of the deterministic
            calculation itself.
    """

    instrument: Instrument
    name: str
    period: int
    frequency: BarFrequency
    source_values: tuple[float, ...]
    values: tuple[float, ...]
    latest_value: float
    as_of: datetime
    computed_at: datetime

    @property
    def label(self) -> str:
        """Return a short, human-readable identifier (e.g. ``"RSI(14)"``)."""
        return f"{self.name.upper()}({self.period})"
