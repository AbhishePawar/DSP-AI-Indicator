"""Tests for SignalGenerator, ExplanationGenerator, and EvidenceGenerator."""

from datetime import UTC, datetime

from contracts.domain.instrument import Instrument
from contracts.enums import AssetClass, BarFrequency, EngineSource, SignalDirection
from dsp.engine.models import IndicatorResult
from dsp.signals.evidence_generator import EvidenceGenerator
from dsp.signals.explanation_generator import ExplanationGenerator
from dsp.signals.rules import RuleOutcome
from dsp.signals.signal_generator import SignalGenerator

_INSTRUMENT = Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")
_AS_OF = datetime(2024, 1, 5, tzinfo=UTC)
_COMPUTED_AT = datetime(2024, 1, 5, 12, 0, tzinfo=UTC)


def _result(latest_value: float = 76.2) -> IndicatorResult:
    return IndicatorResult(
        instrument=_INSTRUMENT,
        name="rsi",
        period=14,
        frequency=BarFrequency.DAILY,
        source_values=(100.0, 101.0),
        values=(float("nan"), latest_value),
        latest_value=latest_value,
        as_of=_AS_OF,
        computed_at=_COMPUTED_AT,
    )


def _outcome(
    direction: SignalDirection = SignalDirection.BEARISH,
    strength: float | None = 0.5,
) -> RuleOutcome:
    return RuleOutcome(
        direction=direction,
        reasoning="RSI(14) is 76.2, above the overbought threshold of 70.0.",
        threshold=70.0,
        strength=strength,
    )


class TestSignalGenerator:
    """Tests for SignalGenerator.generate."""

    def test_generates_signal_with_expected_shape(self) -> None:
        signal = SignalGenerator().generate(_result(), _outcome())
        assert signal.instrument is _INSTRUMENT
        assert signal.source_engine is EngineSource.INDICATOR_ENGINE
        assert signal.name == "rsi_14"
        assert signal.direction is SignalDirection.BEARISH
        assert signal.timestamp == _AS_OF
        assert signal.value == 76.2
        assert signal.strength == 0.5

    def test_embeds_explanation_when_provided(self) -> None:
        explanation = ExplanationGenerator().generate(_result(), _outcome())
        signal = SignalGenerator().generate(
            _result(), _outcome(), explanation=explanation
        )
        assert signal.explanation is explanation

    def test_nan_latest_value_becomes_none(self) -> None:
        result = _result(latest_value=float("nan"))
        outcome = RuleOutcome(direction=SignalDirection.NEUTRAL, reasoning="n/a")
        signal = SignalGenerator().generate(result, outcome)
        assert signal.value is None


class TestExplanationGenerator:
    """Tests for ExplanationGenerator.generate."""

    def test_summary_matches_rule_reasoning(self) -> None:
        outcome = _outcome()
        explanation = ExplanationGenerator().generate(_result(), outcome)
        assert explanation.summary == outcome.reasoning

    def test_source_engine_is_indicator_engine(self) -> None:
        explanation = ExplanationGenerator().generate(_result(), _outcome())
        assert explanation.source_engine is EngineSource.INDICATOR_ENGINE

    def test_inputs_used_reference_the_indicator(self) -> None:
        explanation = ExplanationGenerator().generate(_result(), _outcome())
        assert explanation.inputs_used == ("RSI(14)", "close_price")

    def test_confidence_matches_outcome_strength(self) -> None:
        explanation = ExplanationGenerator().generate(_result(), _outcome())
        assert explanation.confidence == 0.5

    def test_generated_at_matches_result_computed_at(self) -> None:
        explanation = ExplanationGenerator().generate(_result(), _outcome())
        assert explanation.generated_at == _COMPUTED_AT


class TestEvidenceGenerator:
    """Tests for EvidenceGenerator.generate."""

    def test_claim_matches_rule_reasoning(self) -> None:
        outcome = _outcome()
        evidence = EvidenceGenerator().generate(_result(), outcome)
        assert evidence.claim == outcome.reasoning

    def test_reference_is_the_indicator_label(self) -> None:
        evidence = EvidenceGenerator().generate(_result(), _outcome())
        assert evidence.reference == "RSI(14)"

    def test_value_matches_latest_value(self) -> None:
        evidence = EvidenceGenerator().generate(_result(), _outcome())
        assert evidence.value == 76.2

    def test_weight_matches_outcome_strength(self) -> None:
        evidence = EvidenceGenerator().generate(_result(), _outcome())
        assert evidence.weight == 0.5

    def test_embeds_explanation_when_provided(self) -> None:
        explanation = ExplanationGenerator().generate(_result(), _outcome())
        evidence = EvidenceGenerator().generate(_result(), _outcome(), explanation)
        assert evidence.explanation is explanation

    def test_nan_latest_value_becomes_none(self) -> None:
        result = _result(latest_value=float("nan"))
        outcome = RuleOutcome(direction=SignalDirection.NEUTRAL, reasoning="n/a")
        evidence = EvidenceGenerator().generate(result, outcome)
        assert evidence.value is None
