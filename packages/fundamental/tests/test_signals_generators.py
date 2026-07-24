"""Tests for the Signal/Explanation/Evidence generator trio."""

from datetime import UTC, date, datetime

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, EngineSource, SignalDirection
from fundamental.enums import MetricUnit
from fundamental.models import FundamentalMetric
from fundamental.signals.evidence_generator import EvidenceGenerator
from fundamental.signals.explanation_generator import ExplanationGenerator
from fundamental.signals.rules import BusinessRuleOutcome
from fundamental.signals.signal_generator import BusinessSignalGenerator

_INSTRUMENT = Instrument(symbol="TEST", asset_class=AssetClass.EQUITY, currency="USD")
_METRIC = FundamentalMetric(
    instrument=_INSTRUMENT,
    name="roe",
    value=0.20,
    unit=MetricUnit.PERCENT,
    period_end=date(2024, 12, 31),
)
_OUTCOME = BusinessRuleOutcome(
    direction=SignalDirection.BULLISH,
    observation="Strong Profitability",
    reasoning="ROE is 20.0%, above the threshold of 15.0%.",
    threshold=0.15,
    strength=0.8,
)
_NOW = datetime(2024, 6, 1, tzinfo=UTC)


class TestBusinessSignalGenerator:
    """Tests for BusinessSignalGenerator.generate."""

    def test_builds_signal_from_metric_and_outcome(self) -> None:
        signal = BusinessSignalGenerator().generate(_METRIC, _OUTCOME)
        assert signal.instrument is _INSTRUMENT
        assert signal.source_engine is EngineSource.FUNDAMENTAL_ENGINE
        assert signal.name == "roe"
        assert signal.direction is SignalDirection.BULLISH
        assert signal.value == 0.20
        assert signal.strength == 0.8

    def test_timestamp_derived_from_period_end(self) -> None:
        signal = BusinessSignalGenerator().generate(_METRIC, _OUTCOME)
        assert signal.timestamp == datetime(2024, 12, 31, tzinfo=UTC)

    def test_explanation_is_embedded_when_provided(self) -> None:
        explanation = ExplanationGenerator().generate(
            _METRIC, _OUTCOME, generated_at=_NOW
        )
        signal = BusinessSignalGenerator().generate(
            _METRIC, _OUTCOME, explanation=explanation
        )
        assert signal.explanation is explanation


class TestExplanationGenerator:
    """Tests for ExplanationGenerator.generate."""

    def test_summary_matches_outcome_reasoning_verbatim(self) -> None:
        explanation = ExplanationGenerator().generate(
            _METRIC, _OUTCOME, generated_at=_NOW
        )
        assert explanation.summary == _OUTCOME.reasoning
        assert explanation.source_engine is EngineSource.FUNDAMENTAL_ENGINE
        assert explanation.confidence == _OUTCOME.strength
        assert explanation.generated_at == _NOW

    def test_inputs_used_reference_metric_and_observation(self) -> None:
        explanation = ExplanationGenerator().generate(
            _METRIC, _OUTCOME, generated_at=_NOW
        )
        assert explanation.inputs_used == ("ROE", "Strong Profitability")


class TestEvidenceGenerator:
    """Tests for EvidenceGenerator.generate."""

    def test_claim_matches_outcome_reasoning_verbatim(self) -> None:
        evidence = EvidenceGenerator().generate(_METRIC, _OUTCOME)
        assert evidence.claim == _OUTCOME.reasoning
        assert evidence.source_engine is EngineSource.FUNDAMENTAL_ENGINE
        assert evidence.value == 0.20
        assert evidence.reference == "ROE"
        assert evidence.weight == _OUTCOME.strength

    def test_embeds_provided_explanation(self) -> None:
        explanation = ExplanationGenerator().generate(
            _METRIC, _OUTCOME, generated_at=_NOW
        )
        evidence = EvidenceGenerator().generate(_METRIC, _OUTCOME, explanation)
        assert evidence.explanation is explanation
