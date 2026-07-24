"""Canonical assembly helpers for Data Engine contract outputs.

``FinancialSnapshot`` and ``EconomicSnapshot`` live in their respective
engines and must not be constructed here. Builders produce the ordered
``contracts`` values those snapshots wrap — Sprint 6.4 performs the wrap.
"""

from __future__ import annotations

from contracts.domain.economic_series import EconomicSeries
from contracts.domain.fundamental_statement import FundamentalStatement
from contracts.domain.instrument import Instrument
from data_engine.exceptions import InvalidProviderDataError

__all__ = ["EconomicSeriesBuilder", "FundamentalStatementsBuilder"]


class FundamentalStatementsBuilder:
    """Validate and order ``FundamentalStatement`` values for engine handoff.

    Mirrors the structural guarantees expected by the Fundamental
    Engine's ``FinancialSnapshot`` (non-empty, single instrument, unique
    ``period_end``, most-recent-first) while remaining entirely inside
    ``data_engine`` and emitting only ``contracts`` types.
    """

    @staticmethod
    def build(
        instrument: Instrument,
        statements: tuple[FundamentalStatement, ...] | list[FundamentalStatement],
        *,
        allow_empty: bool = False,
    ) -> tuple[FundamentalStatement, ...]:
        """Assemble a canonical, most-recent-first statement tuple.

        Args:
            instrument: Instrument every statement must belong to.
            statements: Statements to assemble (any order).
            allow_empty: When ``True``, an empty input returns ``()``
                instead of raising. Ports that require at least one
                period should leave this ``False``.

        Returns:
            Statements ordered most-recent-first.

        Raises:
            InvalidProviderDataError: If statements are empty (and
                ``allow_empty`` is ``False``), belong to a different
                instrument, or contain duplicate ``period_end`` values.
        """
        ordered = tuple(
            sorted(statements, key=lambda item: item.period_end, reverse=True)
        )
        if not ordered:
            if allow_empty:
                return ()
            msg = "statements must not be empty"
            raise InvalidProviderDataError(msg)

        seen: set[object] = set()
        for statement in ordered:
            if statement.instrument != instrument:
                msg = (
                    "all statements must belong to instrument "
                    f"'{instrument.symbol}', found '{statement.instrument.symbol}'"
                )
                raise InvalidProviderDataError(msg)
            if statement.period_end in seen:
                msg = (
                    f"duplicate period_end {statement.period_end.isoformat()} "
                    f"for '{instrument.symbol}'"
                )
                raise InvalidProviderDataError(msg)
            seen.add(statement.period_end)

        return ordered


class EconomicSeriesBuilder:
    """Validate a ``EconomicSeries`` for engine handoff.

    ``contracts.EconomicSeries`` already enforces non-empty, ascending,
    duplicate-free points. This builder re-checks identity fields and
    optionally truncates to the most-recent ``limit`` observations while
    preserving ascending order — the shape Sprint 6.4 will project into
    ``EconomicSnapshot``.
    """

    @staticmethod
    def build(
        series: EconomicSeries,
        *,
        expected_indicator_code: str | None = None,
        expected_country: str | None = None,
        limit: int | None = None,
    ) -> EconomicSeries:
        """Return a validated (optionally truncated) economic series.

        Args:
            series: Already-normalized ``EconomicSeries``.
            expected_indicator_code: Optional code that ``series`` must
                match (case-insensitive).
            expected_country: Optional country that ``series`` must match.
            limit: Optional maximum number of most-recent observations
                to retain. ``None`` keeps the full series.

        Returns:
            The validated series (possibly truncated).

        Raises:
            InvalidProviderDataError: If identity checks fail or
                ``limit`` is negative.
            DataEngineError: Never — use ``InvalidProviderDataError``.
        """
        if limit is not None and limit < 0:
            msg = f"limit must be non-negative, got {limit}"
            raise InvalidProviderDataError(msg)

        if expected_indicator_code is not None:
            expected = expected_indicator_code.strip().upper()
            if series.indicator_code != expected:
                msg = (
                    f"series indicator_code '{series.indicator_code}' does not "
                    f"match expected '{expected}'"
                )
                raise InvalidProviderDataError(msg)

        if expected_country is not None:
            expected = expected_country.strip().upper()
            if series.country != expected:
                msg = (
                    f"series country '{series.country}' does not match "
                    f"expected '{expected}'"
                )
                raise InvalidProviderDataError(msg)

        if not series.points:
            msg = "economic series points must not be empty"
            raise InvalidProviderDataError(msg)

        if limit is None or limit >= len(series.points):
            return series

        # Keep the most-recent `limit` points; contracts require ascending.
        trimmed = series.points[-limit:]
        return EconomicSeries(
            indicator_code=series.indicator_code,
            indicator_name=series.indicator_name,
            country=series.country,
            frequency=series.frequency,
            points=trimmed,
            unit=series.unit,
        )
