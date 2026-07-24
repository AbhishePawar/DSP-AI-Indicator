"""Platform integration: single pipeline execution for Decision Pack."""

from __future__ import annotations

from datetime import UTC, date, datetime

from ai_committee import (
    CommitteeReport,
    Decision,
    InvestmentDecision,
    MemberVote,
    Opinion,
)
from contracts import (
    AssetClass,
    EngineSource,
    Evidence,
    Instrument,
    Recommendation,
    RecommendationAction,
)
from dsp_platform import AnalysisRequest, DSPPlatform, DecisionPack
from recommendation import RecommendationMapper

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


class _CountingAnalysis:
    def __init__(self, report: CommitteeReport) -> None:
        self.report = report
        self.analyze_calls = 0
        self.analyze_recommendation_calls = 0

    def analyze(self, request: AnalysisRequest) -> CommitteeReport:
        self.analyze_calls += 1
        return self.report

    def analyze_recommendation(self, request: AnalysisRequest) -> Recommendation:
        self.analyze_recommendation_calls += 1
        return RecommendationMapper.map(self.report)


def _report(instrument: Instrument) -> CommitteeReport:
    op = Opinion(
        source="technical",
        recommendation=Decision.BUY,
        reasoning="Trend support.",
        evidence=(
            Evidence(
                source_engine=EngineSource.INDICATOR_ENGINE,
                claim="trend up",
                value=1.0,
                reference="test",
                weight=0.8,
            ),
        ),
        engine=EngineSource.AI_COMMITTEE,
    )
    return CommitteeReport(
        instrument=instrument,
        opinions=(op,),
        votes=(
            MemberVote(
                source="technical", recommendation=Decision.BUY, opinion=op
            ),
        ),
        decision=InvestmentDecision(
            instrument=instrument,
            decision=Decision.BUY,
            rationale="Buy.",
            decided_at=FIXED_NOW,
        ),
        voting_summary="1/1 buy",
        explanation="Aligned.",
    )


class TestPipelineOnce:
    def test_analyze_decision_pack_runs_analyze_once(self) -> None:
        instrument = Instrument(
            symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
        )
        counting = _CountingAnalysis(_report(instrument))
        platform = DSPPlatform(analysis_service=counting)  # type: ignore[arg-type]
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        pack = platform.analyze_decision_pack(request)
        assert isinstance(pack, DecisionPack)
        assert counting.analyze_calls == 1
        assert counting.analyze_recommendation_calls == 0
        assert pack.recommendation.action is RecommendationAction.BUY

    def test_analyze_still_uses_recommendation_path(self) -> None:
        instrument = Instrument(
            symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD"
        )
        counting = _CountingAnalysis(_report(instrument))
        platform = DSPPlatform(analysis_service=counting)  # type: ignore[arg-type]
        request = AnalysisRequest(
            instrument=instrument,
            start=date(2024, 1, 1),
            end=date(2024, 6, 1),
        )
        result = platform.analyze(request)
        assert result.action is RecommendationAction.BUY
        assert counting.analyze_recommendation_calls == 1
        assert counting.analyze_calls == 0
