"""AI Investment Committee public API.

The AI Investment Committee synthesizes explainable outputs from
upstream analytical engines into one investment decision and an
auditable deliberation report. Sprint 8.1 adds the Valuation Member
alongside Technical, Fundamental, and Economic — still no LLM
reasoning and no weighted voting.

See ``packages/ai_committee/README.md`` for the full flow.
"""

from ai_committee.committee import InvestmentCommittee
from ai_committee.enums import Decision
from ai_committee.exceptions import CommitteeError
from ai_committee.members import (
    CommitteeMember,
    EconomicMember,
    FundamentalMember,
    TechnicalMember,
    ValuationMember,
)
from ai_committee.models import (
    CommitteeInput,
    CommitteeReport,
    InvestmentDecision,
    MemberVote,
    Opinion,
)
from ai_committee.voting import (
    aggregate_recommendations,
    collapse_signals,
    signal_direction_to_decision,
)

__all__ = [
    "CommitteeError",
    "CommitteeInput",
    "CommitteeMember",
    "CommitteeReport",
    "Decision",
    "EconomicMember",
    "FundamentalMember",
    "InvestmentCommittee",
    "InvestmentDecision",
    "MemberVote",
    "Opinion",
    "TechnicalMember",
    "ValuationMember",
    "aggregate_recommendations",
    "collapse_signals",
    "signal_direction_to_decision",
]

__version__ = "0.3.0"
