"""Shared fixtures and builders for Decision Intelligence B3 tests."""

from __future__ import annotations

from datetime import UTC, date, datetime

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
    Recommendation,
    RecommendationAction,
    ValuationSummary,
)
from decision_intelligence import DecisionIntelligenceService, DecisionPack
from recommendation import RecommendationMapper

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def instrument() -> Instrument:
    return Instrument(symbol="AAPL", asset_class=AssetClass.EQUITY, currency="USD")


@pytest.fixture
def service() -> DecisionIntelligenceService:
    return DecisionIntelligenceService()


def evidence(claim: str, *, engine: EngineSource = EngineSource.AI_COMMITTEE) -> Evidence:
    return Evidence(
        source_engine=engine,
        claim=claim,
        value=1.0,
        reference="test",
        weight=0.5,
    )


def available_mos(*, ratio: float = 0.25) -> MarginOfSafety:
    intrinsic = 100.0
    market = intrinsic * (1.0 - ratio)
    return MarginOfSafety(
        ratio=ratio,
        intrinsic_value=intrinsic,
        market_value=market,
        available=True,
    )


def unavailable_mos() -> MarginOfSafety:
    return MarginOfSafety(
        ratio=None,
        intrinsic_value=None,
        market_value=None,
        available=False,
    )


def valuation_summary(mos: MarginOfSafety) -> ValuationSummary:
    return ValuationSummary(
        intrinsic_low=90.0,
        intrinsic_mid=100.0,
        intrinsic_high=110.0,
        margin_of_safety=mos,
        confidence="medium",
        currency="USD",
        as_of=date(2024, 6, 1),
    )


def make_report(
    instrument: Instrument,
    *,
    decision: Decision,
    member_decisions: tuple[Decision, ...],
    sources: tuple[str, ...] | None = None,
    mos: MarginOfSafety | None = None,
    with_valuation_summary: bool = False,
) -> CommitteeReport:
    default_sources = ("technical", "fundamental", "economic", "valuation")
    src = sources or default_sources[: len(member_decisions)]
    opinions: list[Opinion] = []
    votes: list[MemberVote] = []
    for source, member_decision in zip(src, member_decisions, strict=True):
        kwargs: dict = {}
        if source == "valuation":
            kwargs["margin_of_safety"] = mos
            if with_valuation_summary and mos is not None:
                kwargs["valuation_summary"] = valuation_summary(mos)
        op = Opinion(
            source=source,
            recommendation=member_decision,
            reasoning=f"{source} reasons for {member_decision.value}",
            evidence=(evidence(f"{source} evidence"),),
            engine=EngineSource.AI_COMMITTEE,
            **kwargs,
        )
        opinions.append(op)
        votes.append(
            MemberVote(
                source=source,
                recommendation=member_decision,
                opinion=op,
            )
        )
    investment = InvestmentDecision(
        instrument=instrument,
        decision=decision,
        rationale=f"Committee decides {decision.value}.",
        decided_at=FIXED_NOW,
    )
    return CommitteeReport(
        instrument=instrument,
        opinions=tuple(opinions),
        votes=tuple(votes),
        decision=investment,
        voting_summary=f"votes={[d.value for d in member_decisions]}",
        explanation="Full deliberation narrative.",
    )


def make_recommendation(
    report: CommitteeReport,
    *,
    margin_of_safety: MarginOfSafety | None = None,
) -> Recommendation:
    mapped = RecommendationMapper.map(report)
    if margin_of_safety is None:
        return mapped
    return Recommendation(
        instrument=mapped.instrument,
        action=mapped.action,
        conviction=mapped.conviction,
        rationale=mapped.rationale,
        supporting_evidence=mapped.supporting_evidence,
        dissenting_views=mapped.dissenting_views,
        generated_at=mapped.generated_at,
        margin_of_safety=margin_of_safety,
        valuation_summary=mapped.valuation_summary,
    )


def build_pack(
    instrument: Instrument,
    *,
    decision: Decision,
    member_decisions: tuple[Decision, ...],
    sources: tuple[str, ...] | None = None,
    mos: MarginOfSafety | None = None,
    with_valuation_summary: bool = False,
    service: DecisionIntelligenceService | None = None,
) -> DecisionPack:
    report = make_report(
        instrument,
        decision=decision,
        member_decisions=member_decisions,
        sources=sources,
        mos=mos,
        with_valuation_summary=with_valuation_summary,
    )
    recommendation = RecommendationMapper.map(report)
    svc = service or DecisionIntelligenceService()
    return svc.build_pack(report, recommendation)


__all__ = [
    "FIXED_NOW",
    "RecommendationAction",
    "available_mos",
    "build_pack",
    "evidence",
    "make_recommendation",
    "make_report",
    "unavailable_mos",
    "valuation_summary",
]
