"""Internal data models for the Fundamental Engine.

None of :class:`FinancialSnapshot`, :class:`FundamentalMetric`, or
:class:`FundamentalResult` is a ``contracts`` type. They exist purely to
carry data between :mod:`fundamental.analyzers`,
:class:`~fundamental.engine.service.FundamentalEngine`, and the
signal-generation components in :mod:`fundamental.signals`; other engines
must never import them directly, and they may change shape without being
treated as a breaking change to the platform's shared vocabulary. The
only stable, cross-engine output of this package is the
``contracts.Signal`` / ``contracts.Explanation`` / ``contracts.Evidence``
triple produced by
:meth:`~fundamental.engine.service.FundamentalEngine.analyze`.

These models live at the top level of the package — sibling to
``engine/``, ``analyzers/``, and ``signals/`` — rather than nested under
``fundamental.engine`` (unlike ``dsp.engine.models``). Every analyzer in
:mod:`fundamental.analyzers` returns :class:`FundamentalMetric` objects
directly (there is no separate raw-array boundary to cross, the way
``dsp.indicators`` crosses from NumPy into ``dsp.engine.models``), so
:mod:`fundamental.analyzers` must import these models independently of
:mod:`fundamental.engine`. Nesting them under ``engine`` would force
importing any analyzer module to first fully initialize
``fundamental.engine`` (a regular package's ``__init__.py`` always runs
before any of its submodules are considered importable) — which in turn
imports :mod:`fundamental.registry`, which imports the analyzers
themselves, a genuine circular import. Keeping the models as a leaf
module with no dependency on ``engine``, ``analyzers``, ``registry``, or
``signals`` avoids that cycle entirely.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from core.exceptions import ValidationError
from fundamental.enums import MetricUnit

#: Display label for a metric name, used to render human-readable
#: explanations and evidence. Metrics without an explicit entry fall
#: back to a title-cased version of their name (see
#: :attr:`FundamentalMetric.label`), so registering a new metric never
#: requires touching this table.
_METRIC_LABELS: dict[str, str] = {
    "revenue_growth": "Revenue Growth",
    "eps_growth": "EPS Growth",
    "roe": "ROE",
    "roce": "ROCE",
    "debt_to_equity": "Debt-to-Equity",
    "operating_margin": "Operating Margin",
    "free_cash_flow": "Free Cash Flow",
}


def format_metric_value(value: float, unit: MetricUnit) -> str:
    """Render a metric value as a human-readable string for its unit.

    Args:
        value: The numeric value to render.
        unit: How the value should be interpreted for display.

    Returns:
        ``"18.0%"`` for :attr:`MetricUnit.PERCENT`, ``"$1,234"`` for
        :attr:`MetricUnit.CURRENCY`, or ``"1.20x"`` for
        :attr:`MetricUnit.RATIO`.
    """
    if unit is MetricUnit.PERCENT:
        return f"{value * 100:.1f}%"
    if unit is MetricUnit.CURRENCY:
        return f"${value:,.0f}"
    return f"{value:.2f}x"


@dataclass(frozen=True, slots=True)
class FinancialSnapshot:
    """One instrument's as-reported financial statements, most-recent-first.

    This is the Fundamental Engine's counterpart to
    ``contracts.PriceSeries``: a validated, ordered bundle of
    ``contracts.FundamentalStatement`` periods for a single instrument,
    matching the ordering already documented by
    ``data_engine.ports.FundamentalsDataPort.get_fundamental_statements``
    ("most recent to oldest").

    Attributes:
        instrument: The instrument every statement belongs to.
        statements: Financial statements ordered most-recent-first, with
            no duplicate reporting periods.
    """

    instrument: Instrument
    statements: tuple[FundamentalStatement, ...]

    def __post_init__(self) -> None:
        """Validate non-emptiness, instrument consistency, and ordering.

        Raises:
            ValidationError: If ``statements`` is empty, contains a
                statement for a different instrument, contains a
                duplicate ``period_end``, or is not ordered
                most-recent-first.
        """
        statements = tuple(self.statements)
        if not statements:
            msg = "statements must not be empty"
            raise ValidationError(msg)

        for statement in statements:
            if statement.instrument != self.instrument:
                msg = (
                    "all statements must belong to the snapshot's "
                    f"instrument ({self.instrument.symbol}), found "
                    f"{statement.instrument.symbol}"
                )
                raise ValidationError(msg)

        period_ends = [statement.period_end for statement in statements]
        if len(set(period_ends)) != len(period_ends):
            msg = "statements must not contain duplicate period_end dates"
            raise ValidationError(msg)
        if period_ends != sorted(period_ends, reverse=True):
            msg = "statements must be ordered most-recent-first"
            raise ValidationError(msg)

        object.__setattr__(self, "statements", statements)

    @property
    def latest(self) -> FundamentalStatement:
        """Return the most recent reporting period."""
        return self.statements[0]

    @property
    def previous(self) -> FundamentalStatement | None:
        """Return the prior reporting period, or ``None`` if unavailable."""
        return self.statements[1] if len(self.statements) > 1 else None


@dataclass(frozen=True, slots=True)
class FundamentalMetric:
    """One computed business metric for one reporting period.

    Attributes:
        instrument: The instrument this metric describes. Carried
            directly on the metric (rather than only on the enclosing
            :class:`FundamentalResult`) so downstream consumers — the
            signal/explanation/evidence generators in
            :mod:`fundamental.signals` — can build a complete
            ``contracts.Signal`` from a metric alone, mirroring how
            ``dsp.engine.models.IndicatorResult`` carries its own
            ``instrument``.
        name: Canonical metric identifier (e.g. ``"roe"``), normalized
            to lowercase. Used to look up display labels and business
            rules.
        value: The computed value, or ``None`` if it could not be
            computed (e.g. a required line item was not reported, or a
            prior period was unavailable for a growth metric). ``None``
            is used instead of ``float("nan")`` — unlike the Indicator
            Engine's numeric series, financial statements routinely omit
            fields, and ``contracts.FundamentalStatement`` already models
            "not reported" as ``None`` for the same reason.
        unit: How ``value`` should be interpreted for display.
        period_end: The reporting period this metric describes.
    """

    instrument: Instrument
    name: str
    value: float | None
    unit: MetricUnit
    period_end: date

    def __post_init__(self) -> None:
        """Normalize the metric name.

        Raises:
            ValidationError: If ``name`` is empty.
        """
        name = self.name.strip().lower()
        if not name:
            msg = "name must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "name", name)

    @property
    def label(self) -> str:
        """Return a short, human-readable label (e.g. ``"ROE"``)."""
        return _METRIC_LABELS.get(self.name, self.name.replace("_", " ").title())

    @property
    def formatted_value(self) -> str | None:
        """Return ``value`` rendered for its unit, or ``None`` if unset."""
        if self.value is None:
            return None
        return format_metric_value(self.value, self.unit)


@dataclass(frozen=True, slots=True)
class FundamentalResult:
    """The outcome of running one analyzer against one snapshot.

    Attributes:
        instrument: The instrument that was analyzed.
        analyzer_name: Canonical analyzer identifier (matches
            ``Analyzer.name``).
        metrics: Every metric the analyzer computed, in a stable order.
        computed_at: Timezone-aware timestamp of when this computation
            ran — execution metadata, not part of the deterministic
            calculation itself.
    """

    instrument: Instrument
    analyzer_name: str
    metrics: tuple[FundamentalMetric, ...]
    computed_at: datetime
