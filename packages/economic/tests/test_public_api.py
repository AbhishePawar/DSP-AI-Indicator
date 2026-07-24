"""Tests for the economic public re-export surface."""

from __future__ import annotations

import economic


class TestPublicApi:
    """Verify the intentional public surface."""

    def test_required_exports(self) -> None:
        assert economic.EconomicEngine is not None
        assert economic.EconomicSnapshot is not None
        assert economic.EconomicAssessment is not None
        assert economic.EconomicSignal is not None
        assert economic.EconomicCondition is not None
        assert economic.EconomicError is not None

    def test_recommendation_exported(self) -> None:
        # Needed by EconomicAssessment.recommendation consumers.
        assert economic.Recommendation is not None

    def test_all_matches_exports(self) -> None:
        for name in economic.__all__:
            assert hasattr(economic, name)

    def test_analyzers_not_in_top_level_all(self) -> None:
        assert "GdpAnalyzer" not in economic.__all__
        assert "Analyzer" not in economic.__all__
