"""Qualitative comparison engine tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
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
    MarginOfSafety,
)
from decision_intelligence import (
    AssuranceLevel,
    DecisionIntelligenceService,
    DecisionPack,
)
from industry import (
    EligibilityOptions,
    IndustryMethodologyRegistry,
    InstrumentIndustryRegistry,
    InvestmentCharacteristicsRegistry,
    PeerEligibilityEvaluator,
    PeerEligibilityPolicyRegistry,
    IndustryTaxonomy,
    seed_peer_eligibility_context,
)
from recommendation import RecommendationMapper
from universe import (
    InvestmentUniverse,
    MultiStockAnalysisRequest,
    MultiStockAnalysisService,
    summarize_decision_pack,
)

from comparison import (
    ComparisonError,
    ComparisonObservation,
    ComparisonStatus,
    QualitativeComparisonEngine,
    compare_universe_result,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _instrument(symbol: str) -> Instrument:
    return Instrument(
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        currency="INR",
        name=symbol,
        country="IN",
    )


def _opinion(source: str, decision: Decision) -> Opinion:
    return Opinion(
        source=source,
        recommendation=decision,
        reasoning=f"{source} for {decision.value}",
        evidence=(
            Evidence(
                source_engine=EngineSource.AI_COMMITTEE,
                claim=f"{source} evidence",
                value=1.0,
                reference="t",
                weight=0.5,
            ),
        ),
        engine=EngineSource.AI_COMMITTEE,
    )


def make_pack(
    instrument: Instrument,
    *,
    decision: Decision = Decision.BUY,
) -> DecisionPack:
    sources = ("technical", "fundamental", "economic")
    decisions = (decision, decision, Decision.HOLD)
    opinions = []
    votes = []
    for source, member in zip(sources, decisions, strict=True):
        op = _opinion(source, member)
        opinions.append(op)
        votes.append(MemberVote(source=source, recommendation=member, opinion=op))
    report = CommitteeReport(
        instrument=instrument,
        opinions=tuple(opinions),
        votes=tuple(votes),
        decision=InvestmentDecision(
            instrument=instrument,
            decision=decision,
            rationale=f"Committee {decision.value}",
            decided_at=FIXED_NOW,
        ),
        voting_summary="synthetic",
        explanation="synthetic",
    )
    recommendation = RecommendationMapper.map(report)
    return DecisionIntelligenceService().build_pack(report, recommendation)


def _engine() -> QualitativeComparisonEngine:
    tax = IndustryTaxonomy()
    chars = InvestmentCharacteristicsRegistry()
    methods = IndustryMethodologyRegistry(tax, chars)
    policies = PeerEligibilityPolicyRegistry(tax)
    assignments = InstrumentIndustryRegistry(tax)
    seed_peer_eligibility_context(tax, chars, methods, policies, assignments)
    evaluator = PeerEligibilityEvaluator(
        assignments=assignments,
        methodologies=methods,
        policies=policies,
    )
    return QualitativeComparisonEngine(
        evaluator=evaluator, methodologies=methods
    )


def _with_mos(pack: DecisionPack, ratio: float) -> DecisionPack:
    mos = MarginOfSafety(
        available=True,
        ratio=ratio,
        intrinsic_value=100.0,
        market_value=100.0 * (1.0 - ratio),
    )
    rec = replace(pack.recommendation, margin_of_safety=mos)
    return replace(pack, recommendation=rec)


def _with_assurance(pack: DecisionPack, level: AssuranceLevel) -> DecisionPack:
    assurance = replace(pack.assurance, assurance_level=level)
    return replace(pack, assurance=assurance)


class TestTwoCompanyComparison:
    def test_direct_peers_complete(self) -> None:
        engine = _engine()
        a = _with_mos(make_pack(_instrument("HDFCBANK")), 0.35)
        b = _with_mos(make_pack(_instrument("ICICIBANK")), 0.20)
        a = _with_assurance(a, AssuranceLevel.HIGH)
        b = _with_assurance(b, AssuranceLevel.MODERATE)
        result = engine.compare_packs((a, b))
        assert result.status is ComparisonStatus.COMPLETE
        report = result.report
        assert report.included_symbols == ("HDFCBANK", "ICICIBANK")
        assert report.excluded_symbols == ()
        assert report.methodology_id == "dsp.methodology.commercial_banking"
        assert report.limitations
        assert report.pair_observations
        assert any("margin of safety" in o.text.lower() for o in report.pair_observations)
        assert any("assurance" in o.text.lower() for o in report.pair_observations)
        # No forbidden ranking language
        blob = " ".join(o.text.lower() for o in report.pair_observations)
        for word in ("better", "best", "winner", "score", "rank"):
            assert word not in blob.split()

    def test_observation_forbidden_words_rejected(self) -> None:
        with pytest.raises(Exception, match="forbidden"):
            ComparisonObservation(code="x", text="A is the better company")


class TestRefusalAndMixed:
    def test_bank_vs_software_refused(self) -> None:
        engine = _engine()
        result = engine.compare_packs(
            (
                make_pack(_instrument("HDFCBANK")),
                make_pack(_instrument("TCS")),
            )
        )
        assert result.status is ComparisonStatus.REFUSED
        assert result.report.included_symbols == ()
        assert result.report.excluded_symbols
        assert result.report.limitations

    def test_missing_methodology_refused(self) -> None:
        engine = _engine()
        # Unbound symbol
        result = engine.compare_packs(
            (
                make_pack(_instrument("HDFCBANK")),
                make_pack(_instrument("NOBIND")),
            )
        )
        assert result.status is ComparisonStatus.REFUSED
        assert any(
            "NOBIND" in r or "binding" in r.lower() or "resolv" in r.lower()
            for r in result.report.exclusion_reasons
        )

    def test_mixed_universe_degraded(self) -> None:
        engine = _engine()
        packs = (
            make_pack(_instrument("HDFCBANK")),
            make_pack(_instrument("ICICIBANK")),
            make_pack(_instrument("TCS")),
        )
        result = engine.compare_packs(packs)
        assert result.status is ComparisonStatus.DEGRADED
        assert set(result.report.included_symbols) == {"HDFCBANK", "ICICIBANK"}
        assert "TCS" in result.report.excluded_symbols
        assert result.report.exclusion_reasons


class TestGroupAndValuation:
    def test_five_company_same_industry(self) -> None:
        engine = _engine()
        # Seed only has HDFC/ICICI for banks — register more via engine's evaluator
        tax = IndustryTaxonomy()
        chars = InvestmentCharacteristicsRegistry()
        methods = IndustryMethodologyRegistry(tax, chars)
        policies = PeerEligibilityPolicyRegistry(tax)
        assignments = InstrumentIndustryRegistry(tax)
        seed_peer_eligibility_context(tax, chars, methods, policies, assignments)
        from industry import InstrumentIndustryAssignment

        for sym in ("BANK01", "BANK02", "BANK03"):
            assignments.register(
                InstrumentIndustryAssignment(
                    symbol=sym,
                    industry_id="dsp.industry.commercial_banking",
                )
            )
        evaluator = PeerEligibilityEvaluator(
            assignments=assignments,
            methodologies=methods,
            policies=policies,
        )
        engine = QualitativeComparisonEngine(
            evaluator=evaluator, methodologies=methods
        )
        packs = tuple(
            make_pack(_instrument(s))
            for s in ("HDFCBANK", "ICICIBANK", "BANK01", "BANK02", "BANK03")
        )
        result = engine.compare_packs(packs)
        assert result.status is ComparisonStatus.COMPLETE
        assert len(result.report.included_symbols) == 5
        assert result.report.shared_observations is not None
        assert result.report.dimension_results

    def test_missing_valuation_limitation(self) -> None:
        engine = _engine()
        a = make_pack(_instrument("HDFCBANK"))
        b = make_pack(_instrument("ICICIBANK"))
        # Default packs may or may not have MoS — force unavailable
        from contracts.domain.margin_of_safety import MarginOfSafety as MoS

        a = replace(
            a,
            recommendation=replace(
                a.recommendation,
                margin_of_safety=MoS(
                    available=False,
                    ratio=None,
                    intrinsic_value=None,
                    market_value=None,
                ),
            ),
        )
        result = engine.compare_packs((a, b))
        assert result.status is ComparisonStatus.COMPLETE
        assert any(
            lim.code == "missing_valuation" for lim in result.report.limitations
        )
        assert any(
            o.code == "valuation_unavailable"
            for o in result.report.valuation_context
        )

    def test_different_robustness(self) -> None:
        engine = _engine()
        a = _with_assurance(make_pack(_instrument("NTPC")), AssuranceLevel.HIGH)
        b = _with_assurance(
            make_pack(_instrument("POWERGRID")), AssuranceLevel.LOW
        )
        result = engine.compare_packs((a, b))
        assert result.status is ComparisonStatus.COMPLETE
        assert any(
            o.code == "assurance_differential"
            for o in result.report.pair_observations
        )


class TestUniverseIntegration:
    def test_compare_universe_result(self) -> None:
        engine = _engine()
        universe = InvestmentUniverse(name="banks")
        universe.add(_instrument("HDFCBANK"))
        universe.add(_instrument("ICICIBANK"))

        class Analyzer:
            def __call__(self, instrument: Instrument) -> DecisionPack:
                return make_pack(instrument)

        from datetime import date

        service = MultiStockAnalysisService(Analyzer())
        multi = service.analyze(
            MultiStockAnalysisRequest(
                universe=universe,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        result = compare_universe_result(engine, multi)
        assert result.status is ComparisonStatus.COMPLETE

    def test_universe_refuses_too_few_packs(self) -> None:
        engine = _engine()
        universe = InvestmentUniverse(name="one")
        universe.add(_instrument("HDFCBANK"))

        class Analyzer:
            def __call__(self, instrument: Instrument) -> DecisionPack:
                return make_pack(instrument)

        from datetime import date

        service = MultiStockAnalysisService(Analyzer())
        multi = service.analyze(
            MultiStockAnalysisRequest(
                universe=universe,
                start=date(2024, 1, 1),
                end=date(2024, 6, 1),
            )
        )
        with pytest.raises(ComparisonError, match="at least two"):
            compare_universe_result(engine, multi)

    def test_summary_projection_unchanged(self) -> None:
        pack = make_pack(_instrument("HDFCBANK"))
        summary = summarize_decision_pack(pack)
        assert summary.instrument.symbol == "HDFCBANK"
