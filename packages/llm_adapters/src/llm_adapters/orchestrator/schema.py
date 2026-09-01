"""Strict Pydantic schema for AI research output.

Malformed or extra-field payloads are rejected. This is not a public
pack — it is an internal AI contract that still must not carry private
routing/provider fields.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    claim: str = Field(min_length=1)


class ResearchSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    unavailable: bool = False


class AIResearchOutput(BaseModel):
    """Structured AI research result. Extra fields are forbidden."""

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    research_status: Literal["complete", "partial", "unavailable", "failed"]
    recommendation: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    valuation: ResearchSection
    business_quality: ResearchSection
    moat: ResearchSection
    management: ResearchSection
    financial_strength: ResearchSection
    earnings_quality: ResearchSection
    growth_quality: ResearchSection
    industry: ResearchSection
    risk: ResearchSection
    buffett_analysis: ResearchSection
    evidence: list[EvidenceItem]
    decision_brief: str = Field(min_length=1)
    limitations: list[str]
    assurance: str = Field(min_length=1)

    def section_map(self) -> dict[str, ResearchSection]:
        return {
            "valuation": self.valuation,
            "business_quality": self.business_quality,
            "moat": self.moat,
            "management": self.management,
            "financial_strength": self.financial_strength,
            "earnings_quality": self.earnings_quality,
            "growth_quality": self.growth_quality,
            "industry": self.industry,
            "risk": self.risk,
            "buffett_analysis": self.buffett_analysis,
        }


REQUIRED_SECTIONS: tuple[str, ...] = (
    "valuation",
    "business_quality",
    "moat",
    "management",
    "financial_strength",
    "earnings_quality",
    "growth_quality",
    "industry",
    "risk",
    "buffett_analysis",
)

# Sections that must cite evidence unless marked unavailable.
EVIDENCE_REQUIRED_SECTIONS: frozenset[str] = frozenset(
    {
        "valuation",
        "business_quality",
        "moat",
        "risk",
        "buffett_analysis",
    }
)


__all__ = [
    "AIResearchOutput",
    "EVIDENCE_REQUIRED_SECTIONS",
    "EvidenceItem",
    "REQUIRED_SECTIONS",
    "ResearchSection",
]
