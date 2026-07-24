"""Tests for the Sprint 3.0 additions to dsp's public API surface."""


class TestPublicApiReExports:
    """Every new orchestration type must be importable from ``dsp`` directly."""

    def test_indicator_engine(self) -> None:
        from dsp import IndicatorEngine
        from dsp.engine.service import IndicatorEngine as Canonical

        assert IndicatorEngine is Canonical

    def test_indicator_spec_and_result(self) -> None:
        from dsp import IndicatorResult, IndicatorSpec
        from dsp.engine.models import IndicatorResult as CanonicalResult
        from dsp.engine.models import IndicatorSpec as CanonicalSpec

        assert IndicatorSpec is CanonicalSpec
        assert IndicatorResult is CanonicalResult

    def test_analysis_result_and_indicator_analysis(self) -> None:
        from dsp import AnalysisResult, IndicatorAnalysis
        from dsp.engine.results import AnalysisResult as CanonicalAnalysisResult
        from dsp.engine.results import IndicatorAnalysis as CanonicalAnalysis

        assert AnalysisResult is CanonicalAnalysisResult
        assert IndicatorAnalysis is CanonicalAnalysis

    def test_default_indicator_specs(self) -> None:
        from dsp import DEFAULT_INDICATOR_SPECS
        from dsp.engine.service import DEFAULT_INDICATOR_SPECS as Canonical

        assert DEFAULT_INDICATOR_SPECS is Canonical

    def test_generators(self) -> None:
        from dsp import EvidenceGenerator, ExplanationGenerator, SignalGenerator
        from dsp.signals.evidence_generator import (
            EvidenceGenerator as CanonicalEvidenceGenerator,
        )
        from dsp.signals.explanation_generator import (
            ExplanationGenerator as CanonicalExplanationGenerator,
        )
        from dsp.signals.signal_generator import (
            SignalGenerator as CanonicalSignalGenerator,
        )

        assert EvidenceGenerator is CanonicalEvidenceGenerator
        assert ExplanationGenerator is CanonicalExplanationGenerator
        assert SignalGenerator is CanonicalSignalGenerator

    def test_existing_exports_still_present(self) -> None:
        from dsp import EMA, RSI, SMA, WMA, Indicator, IndicatorError

        assert all([EMA, RSI, SMA, WMA, Indicator, IndicatorError])
