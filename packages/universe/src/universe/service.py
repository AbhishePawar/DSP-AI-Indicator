"""Multi-stock analysis service — aggregates Decision Packs only."""

from __future__ import annotations

from typing import Protocol

from contracts import Instrument
from decision_intelligence import DecisionPack

from universe.enums import (
    BatchFailurePolicy,
    BatchStatus,
    InstrumentOutcomeStatus,
)
from universe.exceptions import UniverseError
from universe.models import instrument_identity_key
from universe.results import (
    InstrumentAnalysisFailure,
    InstrumentAnalysisOutcome,
    MultiStockAnalysisRequest,
    MultiStockDecisionResult,
)
from universe.summary import ComparableDecisionSummary, summarize_decision_pack

__all__ = [
    "DecisionPackAnalyzer",
    "MultiStockAnalysisService",
]


class DecisionPackAnalyzer(Protocol):
    """Analyzes one instrument through the canonical Decision Pack pipeline."""

    def __call__(self, instrument: Instrument) -> DecisionPack: ...


class MultiStockAnalysisService:
    """Run the canonical single-name pipeline once per universe member.

    Never aggregates raw engine votes. Never recalculates MoS/valuation.
    """

    def __init__(self, analyzer: DecisionPackAnalyzer) -> None:
        self._analyzer = analyzer

    def analyze(
        self, request: MultiStockAnalysisRequest
    ) -> MultiStockDecisionResult:
        """Analyze every instrument; apply the configured failure policy."""
        universe = request.universe
        entries = universe.entries()
        if not entries:
            return MultiStockDecisionResult(
                universe_name=universe.name,
                status=BatchStatus.SUCCESS,
                failure_policy=request.failure_policy,
                outcomes=(),
                analyzed_at_start=request.start,
                analyzed_at_end=request.end,
            )

        outcomes: list[InstrumentAnalysisOutcome] = []
        for index, entry in enumerate(entries):
            instrument = entry.instrument
            try:
                pack = self._analyzer(instrument)
                if instrument_identity_key(
                    pack.recommendation.instrument
                ) != instrument_identity_key(instrument):
                    msg = (
                        "DecisionPack instrument identity mismatch for "
                        f"{instrument.symbol}"
                    )
                    raise UniverseError(msg)
                outcomes.append(
                    InstrumentAnalysisOutcome(
                        instrument=instrument,
                        status=InstrumentOutcomeStatus.SUCCESS,
                        pack=pack,
                    )
                )
            except Exception as exc:
                outcomes.append(
                    InstrumentAnalysisOutcome(
                        instrument=instrument,
                        status=InstrumentOutcomeStatus.FAILURE,
                        failure=InstrumentAnalysisFailure(
                            instrument=instrument,
                            error_type=type(exc).__name__,
                            message=str(exc) or type(exc).__name__,
                        ),
                    )
                )
                if request.failure_policy is BatchFailurePolicy.STRICT:
                    for skipped in entries[index + 1 :]:
                        outcomes.append(
                            InstrumentAnalysisOutcome(
                                instrument=skipped.instrument,
                                status=InstrumentOutcomeStatus.FAILURE,
                                failure=InstrumentAnalysisFailure(
                                    instrument=skipped.instrument,
                                    error_type="SkippedDueToStrictPolicy",
                                    message=(
                                        "Not analyzed because batch failure "
                                        "policy is STRICT and "
                                        f"{instrument.symbol} failed."
                                    ),
                                ),
                            )
                        )
                    break

        return MultiStockDecisionResult(
            universe_name=universe.name,
            status=_batch_status(outcomes),
            failure_policy=request.failure_policy,
            outcomes=tuple(outcomes),
            analyzed_at_start=request.start,
            analyzed_at_end=request.end,
        )

    @staticmethod
    def comparable_summaries(
        result: MultiStockDecisionResult,
    ) -> tuple[ComparableDecisionSummary, ...]:
        """Summaries for successful packs only, in result order."""
        return tuple(
            summarize_decision_pack(outcome.pack)
            for outcome in result.successes
            if outcome.pack is not None
        )


def _batch_status(outcomes: list[InstrumentAnalysisOutcome]) -> BatchStatus:
    if not outcomes:
        return BatchStatus.SUCCESS
    successes = sum(
        1 for o in outcomes if o.status is InstrumentOutcomeStatus.SUCCESS
    )
    failures = len(outcomes) - successes
    if failures == 0:
        return BatchStatus.SUCCESS
    if successes == 0:
        return BatchStatus.FAILURE
    return BatchStatus.PARTIAL_SUCCESS
