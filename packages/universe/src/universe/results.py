"""Multi-stock analysis request and result models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from contracts import Instrument
from core.exceptions import ValidationError
from decision_intelligence import DecisionPack

from universe.enums import (
    BatchFailurePolicy,
    BatchStatus,
    InstrumentOutcomeStatus,
)
from universe.models import InvestmentUniverse, instrument_identity_key

__all__ = [
    "InstrumentAnalysisFailure",
    "InstrumentAnalysisOutcome",
    "MultiStockAnalysisRequest",
    "MultiStockDecisionResult",
]


@dataclass(frozen=True, slots=True)
class MultiStockAnalysisRequest:
    """Shared parameters for analyzing every instrument in a universe.

    Does not embed orchestration types. The platform builds per-instrument
    analysis requests from these fields.
    """

    universe: InvestmentUniverse
    start: date
    end: date
    failure_policy: BatchFailurePolicy = BatchFailurePolicy.PARTIAL

    def __post_init__(self) -> None:
        if self.end < self.start:
            msg = "end must be on or after start"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class InstrumentAnalysisFailure:
    """Structured failure for one instrument (never silently omitted)."""

    instrument: Instrument
    error_type: str
    message: str

    def __post_init__(self) -> None:
        error_type = self.error_type.strip()
        message = self.message.strip()
        if not error_type:
            msg = "error_type must not be empty"
            raise ValidationError(msg)
        if not message:
            msg = "message must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "error_type", error_type)
        object.__setattr__(self, "message", message)


@dataclass(frozen=True, slots=True)
class InstrumentAnalysisOutcome:
    """Success with DecisionPack or structured failure for one instrument."""

    instrument: Instrument
    status: InstrumentOutcomeStatus
    pack: DecisionPack | None = None
    failure: InstrumentAnalysisFailure | None = None

    def __post_init__(self) -> None:
        if self.status is InstrumentOutcomeStatus.SUCCESS:
            if self.pack is None:
                msg = "successful outcome requires DecisionPack"
                raise ValidationError(msg)
            if self.failure is not None:
                msg = "successful outcome must not include failure"
                raise ValidationError(msg)
            if instrument_identity_key(
                self.pack.recommendation.instrument
            ) != instrument_identity_key(self.instrument):
                msg = "pack instrument must match outcome instrument"
                raise ValidationError(msg)
        else:
            if self.failure is None:
                msg = "failed outcome requires structured failure"
                raise ValidationError(msg)
            if self.pack is not None:
                msg = "failed outcome must not include DecisionPack"
                raise ValidationError(msg)
            if instrument_identity_key(
                self.failure.instrument
            ) != instrument_identity_key(self.instrument):
                msg = "failure instrument must match outcome instrument"
                raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class MultiStockDecisionResult:
    """Aggregated Decision Packs (and failures) for one universe run.

    Never ranks securities. Sector comparison is a later phase.
    """

    universe_name: str
    status: BatchStatus
    failure_policy: BatchFailurePolicy
    outcomes: tuple[InstrumentAnalysisOutcome, ...]
    analyzed_at_start: date
    analyzed_at_end: date

    @property
    def successes(self) -> tuple[InstrumentAnalysisOutcome, ...]:
        return tuple(
            o
            for o in self.outcomes
            if o.status is InstrumentOutcomeStatus.SUCCESS
        )

    @property
    def failures(self) -> tuple[InstrumentAnalysisOutcome, ...]:
        return tuple(
            o
            for o in self.outcomes
            if o.status is InstrumentOutcomeStatus.FAILURE
        )

    @property
    def packs(self) -> tuple[DecisionPack, ...]:
        return tuple(o.pack for o in self.successes if o.pack is not None)
