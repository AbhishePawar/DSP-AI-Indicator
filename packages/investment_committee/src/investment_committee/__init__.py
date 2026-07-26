"""Investment Committee public API (FEATURE-008 Phase 1).

Deterministic multi-reviewer consensus. Distinct from frozen
``ai_committee.InvestmentCommittee``.
"""

from __future__ import annotations

from investment_committee.engine import InvestmentCommitteeEngine
from investment_committee.exceptions import (
    InvestmentCommitteeError,
    InvestmentCommitteeValidationError,
)
from investment_committee.metadata import (
    COMMITTEE_VERSION,
    FRAMEWORK_VERSION,
    InvestmentCommitteeMetadata,
)
from investment_committee.models import (
    CommitteeConsensus,
    CommitteeEvidence,
    CommitteeExplainability,
    CommitteeScore,
    CommitteeValidationSummary,
    InvestmentCommitteeConfidence,
    InvestmentCommitteeResult,
    ReviewerOpinion,
)
from investment_committee.scoring import CommitteeDecision, ReviewerRole

__all__ = [
    "COMMITTEE_VERSION",
    "FRAMEWORK_VERSION",
    "CommitteeConsensus",
    "CommitteeDecision",
    "CommitteeEvidence",
    "CommitteeExplainability",
    "CommitteeScore",
    "CommitteeValidationSummary",
    "InvestmentCommitteeConfidence",
    "InvestmentCommitteeEngine",
    "InvestmentCommitteeError",
    "InvestmentCommitteeMetadata",
    "InvestmentCommitteeResult",
    "InvestmentCommitteeValidationError",
    "ReviewerOpinion",
    "ReviewerRole",
]

__version__ = "0.1.0"
