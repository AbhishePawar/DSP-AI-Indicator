"""Decision Intelligence public API.

Sits above Recommendation. Consumes ``CommitteeReport`` +
``contracts.Recommendation`` and produces Decision Brief, Assurance
Assessment, and the investor-facing Decision Pack.
"""

from __future__ import annotations

from decision_intelligence.exceptions import DecisionIntelligenceError
from decision_intelligence.models import (
    AgreementQuality,
    AssuranceAssessment,
    AssuranceLevel,
    AssumptionRiskLevel,
    ConfidenceDriver,
    DecisionBrief,
    DecisionPack,
    DecisionPackEvidenceSummary,
    DecisionResilience,
    DriverDirection,
    EvidenceConsistency,
    EvidenceHighlight,
    GuidanceStance,
    InvalidationSensitivity,
    InvestorGuidance,
    MemberAttribution,
    ReviewTrigger,
    ReviewUrgency,
)
from decision_intelligence.presentation import (
    DecisionPackView,
    present_decision_pack,
)
from decision_intelligence.service import (
    DecisionIntelligenceService,
    attach_evidence_bundle_ref,
)

__all__ = [
    "AgreementQuality",
    "AssuranceAssessment",
    "AssuranceLevel",
    "AssumptionRiskLevel",
    "ConfidenceDriver",
    "DecisionBrief",
    "DecisionIntelligenceError",
    "DecisionIntelligenceService",
    "DecisionPack",
    "DecisionPackEvidenceSummary",
    "DecisionPackView",
    "DecisionResilience",
    "DriverDirection",
    "EvidenceConsistency",
    "EvidenceHighlight",
    "GuidanceStance",
    "InvalidationSensitivity",
    "InvestorGuidance",
    "MemberAttribution",
    "ReviewTrigger",
    "ReviewUrgency",
    "attach_evidence_bundle_ref",
    "present_decision_pack",
]

__version__ = "0.2.0"
