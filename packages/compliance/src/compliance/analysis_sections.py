"""Canonical Company Analysis page section order (PR1.0 architecture)."""

from __future__ import annotations

from enum import StrEnum

__all__ = ["AnalysisSection", "ANALYSIS_PAGE_ORDER"]


class AnalysisSection(StrEnum):
    COMPANY_SNAPSHOT = "company_snapshot"
    RESEARCH_CONCLUSION = "research_conclusion"
    EXECUTIVE_SUMMARY = "executive_summary"
    MARKET_CONSENSUS = "market_consensus"
    BUSINESS_QUALITY = "business_quality"
    FINANCIAL_STRENGTH = "financial_strength"
    GROWTH = "growth"
    VALUATION = "valuation"
    RISK_ANALYSIS = "risk_analysis"
    MANAGEMENT = "management"
    COMPETITIVE_ADVANTAGE = "competitive_advantage"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    AI_COPILOT = "ai_copilot"
    AI_CHALLENGE = "ai_challenge"
    EVIDENCE = "evidence"
    EXPORT = "export"


ANALYSIS_PAGE_ORDER: tuple[AnalysisSection, ...] = (
    AnalysisSection.COMPANY_SNAPSHOT,
    AnalysisSection.RESEARCH_CONCLUSION,
    AnalysisSection.EXECUTIVE_SUMMARY,
    AnalysisSection.MARKET_CONSENSUS,
    AnalysisSection.BUSINESS_QUALITY,
    AnalysisSection.FINANCIAL_STRENGTH,
    AnalysisSection.GROWTH,
    AnalysisSection.VALUATION,
    AnalysisSection.RISK_ANALYSIS,
    AnalysisSection.MANAGEMENT,
    AnalysisSection.COMPETITIVE_ADVANTAGE,
    AnalysisSection.KNOWLEDGE_GRAPH,
    AnalysisSection.AI_COPILOT,
    AnalysisSection.AI_CHALLENGE,
    AnalysisSection.EVIDENCE,
    AnalysisSection.EXPORT,
)

SECTION_TITLES: dict[AnalysisSection, str] = {
    AnalysisSection.COMPANY_SNAPSHOT: "Company Snapshot",
    AnalysisSection.RESEARCH_CONCLUSION: "Research Conclusion",
    AnalysisSection.EXECUTIVE_SUMMARY: "Executive Summary",
    AnalysisSection.MARKET_CONSENSUS: "Market Analyst Consensus",
    AnalysisSection.BUSINESS_QUALITY: "Business Quality",
    AnalysisSection.FINANCIAL_STRENGTH: "Financial Strength",
    AnalysisSection.GROWTH: "Growth",
    AnalysisSection.VALUATION: "Valuation",
    AnalysisSection.RISK_ANALYSIS: "Risk Analysis",
    AnalysisSection.MANAGEMENT: "Management",
    AnalysisSection.COMPETITIVE_ADVANTAGE: "Competitive Advantage",
    AnalysisSection.KNOWLEDGE_GRAPH: "Knowledge Graph",
    AnalysisSection.AI_COPILOT: "AI Copilot",
    AnalysisSection.AI_CHALLENGE: "AI Challenge Mode",
    AnalysisSection.EVIDENCE: "Evidence",
    AnalysisSection.EXPORT: "Export",
}
