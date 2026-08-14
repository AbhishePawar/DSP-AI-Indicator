"""Tests for the default QualitativeComparisonEngine wiring (compare-wiring)."""

from __future__ import annotations

from datetime import UTC, datetime

from ai_committee import CommitteeReport, Decision, InvestmentDecision, MemberVote, Opinion
from comparison import ComparisonStatus, QualitativeComparisonEngine
from contracts import AssetClass, EngineSource, Evidence, Instrument
from decision_intelligence import DecisionIntelligenceService, DecisionPack
from industry import EligibilityOptions
from recommendation import RecommendationMapper

from dsp_platform import (
    DSPPlatform,
    PlatformConfiguration,
    build_default_comparison_engine,
)

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


def _instrument(symbol: str) -> Instrument:
    return Instrument(
        symbol=symbol, asset_class=AssetClass.EQUITY, currency="INR", name=symbol
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


def make_pack(symbol: str, *, decision: Decision = Decision.BUY) -> DecisionPack:
    instrument = _instrument(symbol)
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


def test_build_default_comparison_engine_is_seeded_and_working() -> None:
    engine = build_default_comparison_engine()
    assert isinstance(engine, QualitativeComparisonEngine)
    result = engine.compare_packs(
        (make_pack("HDFCBANK"), make_pack("ICICIBANK"))
    )
    assert result.status is ComparisonStatus.COMPLETE
    assert result.report.included_symbols == ("HDFCBANK", "ICICIBANK")


def _platform() -> DSPPlatform:
    return (
        DSPPlatform.builder()
        .with_configuration(PlatformConfiguration(require_analysis_service=False))
        .build()
    )


def test_compare_companies_resolves_default_engine_when_not_supplied() -> None:
    platform = _platform()
    result = platform.compare_companies(
        (make_pack("HDFCBANK"), make_pack("ICICIBANK"))
    )
    assert result.ok is True
    assert result.capability == "compare_companies"
    assert result.payload.status is ComparisonStatus.COMPLETE
    assert result.payload.report.included_symbols == ("HDFCBANK", "ICICIBANK")


def test_compare_companies_caches_default_engine_on_registry() -> None:
    platform = _platform()
    platform.compare_companies((make_pack("HDFCBANK"), make_pack("ICICIBANK")))
    assert platform.registry.has("comparison_engine")
    first = platform.registry.get("comparison_engine")
    platform.compare_companies((make_pack("HDFCBANK"), make_pack("ICICIBANK")))
    assert platform.registry.get("comparison_engine") is first


def test_compare_companies_honors_explicit_engine_override() -> None:
    platform = _platform()
    custom_engine = build_default_comparison_engine()
    result = platform.compare_companies(
        (make_pack("HDFCBANK"), make_pack("ICICIBANK")),
        engine=custom_engine,
    )
    assert result.ok is True
    assert not platform.registry.has("comparison_engine")


def test_compare_companies_refuses_incompatible_industries_gracefully() -> None:
    platform = _platform()
    result = platform.compare_companies((make_pack("HDFCBANK"), make_pack("TCS")))
    assert result.ok is True
    assert result.payload.status is ComparisonStatus.REFUSED
    assert result.payload.report.included_symbols == ()


def test_compare_companies_second_call_is_served_from_short_ttl_cache() -> None:
    platform = _platform()
    packs = (make_pack("HDFCBANK"), make_pack("ICICIBANK"))

    first = platform.compare_companies(packs)
    assert first.ok is True
    assert first.limitations == ()
    assert platform.registry.has("comparison_cache")

    second = platform.compare_companies(packs)
    assert second.payload is first.payload
    assert any("cache" in note for note in second.limitations)


def test_compare_companies_cache_is_keyed_by_symbols_and_eligibility_options() -> None:
    platform = _platform()
    hdfc_icici = platform.compare_companies(
        (make_pack("HDFCBANK"), make_pack("ICICIBANK"))
    )
    hdfc_icici_related = platform.compare_companies(
        (make_pack("HDFCBANK"), make_pack("ICICIBANK")),
        eligibility_options=EligibilityOptions(allow_related=True),
    )
    assert hdfc_icici.payload is not hdfc_icici_related.payload
    assert hdfc_icici_related.limitations == ()


def test_compare_companies_explicit_engine_bypasses_cache() -> None:
    platform = _platform()
    packs = (make_pack("HDFCBANK"), make_pack("ICICIBANK"))
    custom_engine = build_default_comparison_engine()

    first = platform.compare_companies(packs, engine=custom_engine)
    second = platform.compare_companies(packs, engine=custom_engine)

    assert not platform.registry.has("comparison_cache")
    assert first.payload is not second.payload
    assert second.limitations == ()
