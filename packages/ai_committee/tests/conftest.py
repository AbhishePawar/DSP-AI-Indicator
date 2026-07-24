"""Shared pytest fixtures for AI Investment Committee tests.

Fixtures build contracts DTOs only — never engine-native assessments —
so tests mirror the production committee dependency boundary.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from contracts import (
    AnalyticalStance,
    EconomicContext,
    Evidence,
    Explanation,
    FundamentalContext,
    Instrument,
    MarginOfSafety,
    Signal,
    TechnicalContext,
    ValuationConfidence,
    ValuationContext,
    ValuationSummary,
)
from contracts.enums import (
    AssetClass,
    EngineSource,
    SignalDirection,
)

from ai_committee.models import CommitteeInput

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    """Return a reusable equity instrument fixture."""
    return Instrument(
        symbol="AAPL",
        asset_class=AssetClass.EQUITY,
        currency="USD",
    )


def make_signal(
    instrument: Instrument,
    *,
    name: str,
    direction: SignalDirection,
    source_engine: EngineSource = EngineSource.INDICATOR_ENGINE,
) -> Signal:
    """Build a minimal ``contracts.Signal`` for tests."""
    return Signal(
        instrument=instrument,
        source_engine=source_engine,
        name=name,
        direction=direction,
        timestamp=FIXED_NOW,
        value=1.0,
        strength=0.5,
    )


def make_explanation(
    *,
    source_engine: EngineSource,
    summary: str,
) -> Explanation:
    """Build a minimal ``contracts.Explanation`` for tests."""
    return Explanation(
        source_engine=source_engine,
        summary=summary,
        inputs_used=("test",),
        generated_at=FIXED_NOW,
    )


def make_evidence(
    *,
    source_engine: EngineSource,
    claim: str,
) -> Evidence:
    """Build a minimal ``contracts.Evidence`` for tests."""
    return Evidence(
        source_engine=source_engine,
        claim=claim,
        value=1.0,
        reference="test",
        weight=0.5,
    )


def make_technical_context(
    instrument: Instrument,
    directions: tuple[SignalDirection, ...],
) -> TechnicalContext:
    """Build a TechnicalContext with one signal per direction."""
    signals: list[Signal] = []
    evidence: list[Evidence] = []
    for index, direction in enumerate(directions):
        name = f"ind_{index}"
        signals.append(
            make_signal(
                instrument,
                name=name,
                direction=direction,
                source_engine=EngineSource.INDICATOR_ENGINE,
            )
        )
        evidence.append(
            make_evidence(
                source_engine=EngineSource.INDICATOR_ENGINE,
                claim=f"{name} evidence",
            )
        )
    return TechnicalContext(
        instrument=instrument,
        signals=tuple(signals),
        evidence=tuple(evidence),
    )


def make_fundamental_context(
    instrument: Instrument,
    directions: tuple[SignalDirection, ...],
) -> FundamentalContext:
    """Build a FundamentalContext with one signal per direction."""
    signals: list[Signal] = []
    evidence: list[Evidence] = []
    for index, direction in enumerate(directions):
        name = f"metric_{index}"
        signals.append(
            make_signal(
                instrument,
                name=name,
                direction=direction,
                source_engine=EngineSource.FUNDAMENTAL_ENGINE,
            )
        )
        evidence.append(
            make_evidence(
                source_engine=EngineSource.FUNDAMENTAL_ENGINE,
                claim=f"{name} evidence",
            )
        )
    return FundamentalContext(
        instrument=instrument,
        signals=tuple(signals),
        evidence=tuple(evidence),
    )


def make_economic_context(
    stance: AnalyticalStance,
    *,
    condition: str | None = None,
) -> EconomicContext:
    """Build a minimal EconomicContext for committee tests."""
    if condition is None:
        condition = {
            AnalyticalStance.BUY: "expansion",
            AnalyticalStance.HOLD: "slowing",
            AnalyticalStance.SELL: "contraction",
        }[stance]
    reasoning = f"Economic stance is {stance.value}."
    evidence = make_evidence(
        source_engine=EngineSource.ECONOMIC_ENGINE,
        claim=reasoning,
    )
    return EconomicContext(
        stance=stance,
        overall_condition=condition,
        country="US",
        reasoning=reasoning,
        evidence=(evidence,),
    )


def make_valuation_context(
    instrument: Instrument,
    *,
    mos_ratio: float | None = 0.25,
    confidence: ValuationConfidence = ValuationConfidence.HIGH,
    mid: float | None = 1000.0,
    reasoning: str = "Trading below intrinsic value.",
) -> ValuationContext:
    """Build a ValuationContext with controllable MoS / confidence."""
    available = mos_ratio is not None
    market_value = None
    if available and mid is not None and mos_ratio is not None:
        market_value = mid * (1.0 - mos_ratio)
    evidence = make_evidence(
        source_engine=EngineSource.VALUATION_ENGINE,
        claim=reasoning,
    )
    mos = MarginOfSafety(
        ratio=mos_ratio,
        intrinsic_value=mid,
        market_value=market_value,
        available=available,
    )
    summary = ValuationSummary(
        intrinsic_low=mid,
        intrinsic_mid=mid,
        intrinsic_high=mid,
        margin_of_safety=mos,
        confidence=confidence.value,
        currency="USD",
        as_of=date(2023, 12, 31),
    )
    return ValuationContext(
        instrument=instrument,
        margin_of_safety=mos,
        valuation_summary=summary,
        confidence=confidence,
        reasoning=reasoning,
        evidence=(evidence,),
    )


@pytest.fixture
def technical_factory(instrument: Instrument):
    """Factory fixture for TechnicalContext DTOs."""

    def _factory(
        directions: tuple[SignalDirection, ...],
        *,
        for_instrument: Instrument | None = None,
    ) -> TechnicalContext:
        return make_technical_context(
            for_instrument or instrument, directions
        )

    return _factory


@pytest.fixture
def fundamental_factory(instrument: Instrument):
    """Factory fixture for FundamentalContext DTOs."""

    def _factory(
        directions: tuple[SignalDirection, ...],
        *,
        for_instrument: Instrument | None = None,
    ) -> FundamentalContext:
        return make_fundamental_context(
            for_instrument or instrument, directions
        )

    return _factory


@pytest.fixture
def economic_factory():
    """Factory fixture for EconomicContext DTOs."""

    def _factory(
        stance: AnalyticalStance = AnalyticalStance.BUY,
        *,
        condition: str | None = None,
    ) -> EconomicContext:
        return make_economic_context(stance, condition=condition)

    return _factory


@pytest.fixture
def valuation_factory(instrument: Instrument):
    """Factory fixture for ValuationContext DTOs."""

    def _factory(
        *,
        mos_ratio: float | None = 0.25,
        confidence: ValuationConfidence = ValuationConfidence.HIGH,
        for_instrument: Instrument | None = None,
        reasoning: str = "Trading below intrinsic value.",
    ) -> ValuationContext:
        return make_valuation_context(
            for_instrument or instrument,
            mos_ratio=mos_ratio,
            confidence=confidence,
            reasoning=reasoning,
        )

    return _factory


@pytest.fixture
def context_factory(
    instrument: Instrument,
    technical_factory,
    fundamental_factory,
    economic_factory,
    valuation_factory,
):
    """Factory fixture for CommitteeInput contexts."""

    def _factory(
        *,
        technical_dirs: tuple[SignalDirection, ...] = (
            SignalDirection.BULLISH,
        ),
        fundamental_dirs: tuple[SignalDirection, ...] = (
            SignalDirection.BULLISH,
        ),
        economic_recommendation: AnalyticalStance | None = (
            AnalyticalStance.BUY
        ),
        valuation_mos: float | None = 0.25,
        valuation_confidence: ValuationConfidence = ValuationConfidence.HIGH,
        for_instrument: Instrument | None = None,
        include_economic: bool = True,
        include_valuation: bool = True,
    ) -> CommitteeInput:
        inst = for_instrument or instrument
        economic = None
        if include_economic and economic_recommendation is not None:
            economic = economic_factory(economic_recommendation)
        valuation = None
        if include_valuation:
            valuation = valuation_factory(
                mos_ratio=valuation_mos,
                confidence=valuation_confidence,
                for_instrument=inst,
            )
        return CommitteeInput(
            instrument=inst,
            technical=technical_factory(
                technical_dirs, for_instrument=inst
            ),
            fundamental=fundamental_factory(
                fundamental_dirs, for_instrument=inst
            ),
            economic=economic,
            valuation=valuation,
        )

    return _factory
