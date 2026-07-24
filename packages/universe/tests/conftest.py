"""Shared helpers for universe package tests."""

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
    RecommendationAction,
)
from decision_intelligence import DecisionIntelligenceService, DecisionPack
from recommendation import RecommendationMapper

FIXED_NOW = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
START = date(2024, 1, 1)
END = date(2024, 6, 1)


@pytest.fixture
def equity() -> AssetClass:
    return AssetClass.EQUITY


def make_instrument(
    symbol: str,
    *,
    sector: str | None = None,
    industry: str | None = None,
    exchange: str | None = None,
) -> Instrument:
    return Instrument(
        symbol=symbol,
        asset_class=AssetClass.EQUITY,
        currency="INR",
        name=symbol.title(),
        exchange=exchange,
        sector=sector,
        industry=industry,
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
        votes.append(
            MemberVote(source=source, recommendation=member, opinion=op)
        )
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


class RecordingAnalyzer:
    """Test double that returns packs and records call order."""

    def __init__(
        self,
        *,
        fail_symbols: frozenset[str] | set[str] = (),
        decision: Decision = Decision.BUY,
    ) -> None:
        self.fail_symbols = frozenset(s.upper() for s in fail_symbols)
        self.decision = decision
        self.calls: list[str] = []

    def __call__(self, instrument: Instrument) -> DecisionPack:
        self.calls.append(instrument.symbol)
        if instrument.symbol in self.fail_symbols:
            msg = f"synthetic failure for {instrument.symbol}"
            raise RuntimeError(msg)
        return make_pack(instrument, decision=self.decision)
