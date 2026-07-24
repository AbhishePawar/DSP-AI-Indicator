"""Tests for the ai_committee public re-export surface."""

from __future__ import annotations

import ai_committee


class TestPublicApi:
    """Verify every intended public name is re-exported."""

    def test_committee(self) -> None:
        assert ai_committee.InvestmentCommittee is not None
        assert ai_committee.CommitteeInput is not None

    def test_members(self) -> None:
        assert ai_committee.CommitteeMember is not None
        assert ai_committee.TechnicalMember is not None
        assert ai_committee.FundamentalMember is not None
        assert ai_committee.EconomicMember is not None
        assert ai_committee.ValuationMember is not None

    def test_models(self) -> None:
        assert ai_committee.Opinion is not None
        assert ai_committee.MemberVote is not None
        assert ai_committee.InvestmentDecision is not None
        assert ai_committee.CommitteeReport is not None

    def test_enums_and_voting(self) -> None:
        assert ai_committee.Decision is not None
        assert ai_committee.collapse_signals is not None
        assert ai_committee.aggregate_recommendations is not None
        assert ai_committee.signal_direction_to_decision is not None

    def test_exceptions(self) -> None:
        assert ai_committee.CommitteeError is not None

    def test_all_matches_exports(self) -> None:
        for name in ai_committee.__all__:
            assert hasattr(ai_committee, name)
