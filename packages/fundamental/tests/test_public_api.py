"""Tests for fundamental's public API surface."""


class TestPublicApiReExports:
    """Every public orchestration type must be importable from ``fundamental``."""

    def test_fundamental_engine(self) -> None:
        from fundamental import FundamentalEngine
        from fundamental.engine.service import FundamentalEngine as Canonical

        assert FundamentalEngine is Canonical

    def test_models(self) -> None:
        from fundamental import FinancialSnapshot, FundamentalMetric, FundamentalResult
        from fundamental.models import FinancialSnapshot as CanonicalSnapshot
        from fundamental.models import FundamentalMetric as CanonicalMetric
        from fundamental.models import FundamentalResult as CanonicalResult

        assert FinancialSnapshot is CanonicalSnapshot
        assert FundamentalMetric is CanonicalMetric
        assert FundamentalResult is CanonicalResult

    def test_engine_results(self) -> None:
        from fundamental import CompanyAnalysis, MetricAnalysis
        from fundamental.engine.results import CompanyAnalysis as CanonicalAnalysis
        from fundamental.engine.results import MetricAnalysis as CanonicalMetric

        assert CompanyAnalysis is CanonicalAnalysis
        assert MetricAnalysis is CanonicalMetric

    def test_default_analyzer_names(self) -> None:
        from fundamental import DEFAULT_ANALYZER_NAMES
        from fundamental.engine.service import DEFAULT_ANALYZER_NAMES as Canonical

        assert DEFAULT_ANALYZER_NAMES is Canonical

    def test_generators(self) -> None:
        from fundamental import (
            BusinessSignalGenerator,
            EvidenceGenerator,
            ExplanationGenerator,
        )
        from fundamental.signals.evidence_generator import (
            EvidenceGenerator as CanonicalEvidenceGenerator,
        )
        from fundamental.signals.explanation_generator import (
            ExplanationGenerator as CanonicalExplanationGenerator,
        )
        from fundamental.signals.signal_generator import (
            BusinessSignalGenerator as CanonicalSignalGenerator,
        )

        assert EvidenceGenerator is CanonicalEvidenceGenerator
        assert ExplanationGenerator is CanonicalExplanationGenerator
        assert BusinessSignalGenerator is CanonicalSignalGenerator

    def test_analyzers(self) -> None:
        from fundamental import (
            Analyzer,
            GrowthAnalyzer,
            LeverageAnalyzer,
            ProfitabilityAnalyzer,
            QualityAnalyzer,
        )

        assert all(
            [
                Analyzer,
                GrowthAnalyzer,
                LeverageAnalyzer,
                ProfitabilityAnalyzer,
                QualityAnalyzer,
            ]
        )

    def test_registry_functions_and_error(self) -> None:
        from fundamental import FundamentalError, get, list_analyzers, register

        assert all([FundamentalError, get, list_analyzers, register])
