"""Orchestration service for the Economic Engine."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from contracts.domain.evidence import Evidence
from contracts.enums import EngineSource

import economic.registry as analyzer_registry
from economic.aggregation import aggregate_signals
from economic.analyzers.base import Analyzer
from economic.exceptions import EconomicError
from economic.models import (
    EconomicAssessment,
    EconomicSignal,
    EconomicSnapshot,
)

AnalyzerResolver = Callable[[str], Analyzer]
Clock = Callable[[], datetime]

DEFAULT_ANALYZER_NAMES: tuple[str, ...] = (
    "gdp",
    "inflation",
    "interest_rate",
    "pmi",
    "liquidity",
)


def _default_clock() -> datetime:
    """Return the current, timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class EconomicEngine:
    """Orchestrates macroeconomic analyzers into one assessment.

    The engine never contains ratio/threshold formulas itself — those
    live in the analyzers. Aggregation of signals into condition and
    recommendation lives in :mod:`economic.aggregation`.
    """

    def __init__(
        self,
        *,
        resolve_analyzer: AnalyzerResolver = analyzer_registry.get,
        clock: Clock = _default_clock,
    ) -> None:
        """Initialize with optional injectable collaborators.

        Args:
            resolve_analyzer: Name → analyzer factory. Defaults to the
                shared analyzer registry.
            clock: Timezone-aware clock for ``assessed_at``.
        """
        self._resolve_analyzer = resolve_analyzer
        self._clock = clock

    def analyze(
        self,
        snapshot: EconomicSnapshot,
        *,
        analyzer_names: Sequence[str] | None = None,
    ) -> EconomicAssessment:
        """Analyze a macroeconomic snapshot.

        Args:
            snapshot: Point-in-time macro inputs.
            analyzer_names: Which analyzers to run. Defaults to
                :data:`DEFAULT_ANALYZER_NAMES`.

        Returns:
            A fully explained :class:`EconomicAssessment`.

        Raises:
            EconomicError: If an analyzer name is unknown or an
                analyzer fails.
        """
        selected = (
            tuple(analyzer_names)
            if analyzer_names is not None
            else DEFAULT_ANALYZER_NAMES
        )
        signals: list[EconomicSignal] = []
        for name in selected:
            signals.extend(self._run_analyzer(snapshot, name))

        try:
            condition, recommendation, reasoning = aggregate_signals(signals)
        except ValueError as exc:
            raise EconomicError(str(exc)) from exc

        evidence = tuple(_to_evidence(signal) for signal in signals)
        return EconomicAssessment(
            overall_condition=condition,
            recommendation=recommendation,
            reasoning=reasoning,
            evidence=evidence,
            detected_signals=tuple(signals),
            as_of=snapshot.as_of,
            assessed_at=self._clock(),
            country=snapshot.country,
        )

    def _run_analyzer(
        self,
        snapshot: EconomicSnapshot,
        name: str,
    ) -> tuple[EconomicSignal, ...]:
        """Resolve and execute one analyzer."""
        try:
            analyzer = self._resolve_analyzer(name)
        except KeyError as exc:
            msg = f"unknown economic analyzer: {name!r}"
            raise EconomicError(msg) from exc
        try:
            return analyzer.analyze(snapshot)
        except EconomicError:
            raise
        except Exception as exc:
            msg = f"analyzer {name!r} failed: {exc}"
            raise EconomicError(msg) from exc


def _to_evidence(signal: EconomicSignal) -> Evidence:
    """Map an internal signal onto a ``contracts.Evidence`` item."""
    return Evidence(
        source_engine=EngineSource.ECONOMIC_ENGINE,
        claim=signal.reasoning,
        value=signal.value,
        reference=signal.observation,
        weight=None,
    )
