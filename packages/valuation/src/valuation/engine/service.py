"""Orchestration service for the Valuation Engine."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from contracts.domain.evidence import Evidence
from contracts.domain.valuation_summary import ValuationSummary
from contracts.enums import EngineSource
from fundamental import FinancialSnapshot

import valuation.registry as method_registry
from valuation.aggregation import aggregate_estimates
from valuation.assumptions import ValuationAssumptions
from valuation.exceptions import ValuationError
from valuation.methods.base import ValuationMethodRunner
from valuation.models import (
    IntrinsicValueEstimate,
    MarketSnapshot,
    ValuationAssessment,
    ValuationEvidence,
)

MethodResolver = Callable[[str], ValuationMethodRunner]
Clock = Callable[[], datetime]

DEFAULT_METHOD_NAMES: tuple[str, ...] = (
    "dcf",
    "owner_earnings",
    "earnings_multiple",
    "book_value",
    "residual_income",
)


def _default_clock() -> datetime:
    """Return the current, timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class ValuationEngine:
    """Orchestrates independent valuation methods into one assessment.

    The engine never contains formula bodies itself — those live in
    :mod:`valuation.methods`. Aggregation lives in
    :mod:`valuation.aggregation`.

    Margin of Safety is calculated once during aggregation and emitted
    both on :class:`ValuationAssessment` and as ``contracts.Evidence``.
    """

    def __init__(
        self,
        *,
        assumptions: ValuationAssumptions | None = None,
        resolve_method: MethodResolver = method_registry.get,
        clock: Clock = _default_clock,
    ) -> None:
        """Initialize with optional injectable collaborators.

        Args:
            assumptions: Conservative valuation parameters.
            resolve_method: Name → method factory (defaults to registry).
            clock: Timezone-aware clock for ``assessed_at``.
        """
        self._assumptions = assumptions or ValuationAssumptions()
        self._resolve_method = resolve_method
        self._clock = clock

    @property
    def assumptions(self) -> ValuationAssumptions:
        """Return the immutable assumptions used by this engine."""
        return self._assumptions

    def analyze(
        self,
        snapshot: FinancialSnapshot,
        market: MarketSnapshot | None = None,
        *,
        method_names: Sequence[str] | None = None,
    ) -> ValuationAssessment:
        """Estimate intrinsic value from a financial snapshot.

        Args:
            snapshot: Fundamental statements for one instrument.
            market: Optional market capitalization for margin of safety.
            method_names: Which methods to run. Defaults to
                :data:`DEFAULT_METHOD_NAMES`.

        Returns:
            A deterministic :class:`ValuationAssessment`.

        Raises:
            ValuationError: If a method name is unknown or a method
                raises unexpectedly.
        """
        selected = (
            tuple(method_names)
            if method_names is not None
            else DEFAULT_METHOD_NAMES
        )
        estimates: list[IntrinsicValueEstimate] = []
        for name in selected:
            estimates.append(self._run_method(snapshot, name))

        try:
            (
                valuation_range,
                margin,
                confidence,
                method_evidence,
                reasoning,
            ) = aggregate_estimates(estimates, market)
        except ValueError as exc:
            raise ValuationError(str(exc)) from exc

        evidence = tuple(_to_evidence(item) for item in method_evidence)
        if margin.available and margin.ratio is not None:
            evidence = evidence + (
                Evidence(
                    source_engine=EngineSource.VALUATION_ENGINE,
                    claim=f"Margin of safety={margin.ratio:.2%}",
                    value=margin.ratio,
                    reference="margin_of_safety",
                    weight=None,
                ),
            )

        latest = snapshot.latest
        summary = ValuationSummary(
            intrinsic_low=valuation_range.low,
            intrinsic_mid=valuation_range.mid,
            intrinsic_high=valuation_range.high,
            margin_of_safety=margin,
            confidence=confidence.value,
            currency=latest.currency,
            as_of=latest.period_end,
        )
        return ValuationAssessment(
            instrument=snapshot.instrument,
            estimates=tuple(estimates),
            valuation_range=valuation_range,
            margin_of_safety=margin,
            summary=summary,
            confidence=confidence,
            evidence=evidence,
            method_evidence=method_evidence,
            reasoning=reasoning,
            currency=latest.currency,
            as_of=latest.period_end,
            assessed_at=self._clock(),
        )

    def _run_method(
        self,
        snapshot: FinancialSnapshot,
        name: str,
    ) -> IntrinsicValueEstimate:
        """Resolve and execute one valuation method."""
        try:
            method = self._resolve_method(name)
        except KeyError as exc:
            msg = f"unknown valuation method: {name!r}"
            raise ValuationError(msg) from exc
        try:
            return method.estimate(snapshot, self._assumptions)
        except ValuationError:
            raise
        except Exception as exc:
            msg = f"valuation method {name!r} failed: {exc}"
            raise ValuationError(msg) from exc


def _to_evidence(item: ValuationEvidence) -> Evidence:
    """Map engine-local evidence onto ``contracts.Evidence``."""
    return Evidence(
        source_engine=EngineSource.VALUATION_ENGINE,
        claim=item.claim,
        value=item.value,
        reference=item.reference or item.method.value,
        weight=None,
    )
