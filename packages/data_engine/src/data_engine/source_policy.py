"""Approved-source whitelist (SIMPLE-14G / SIMPLE-14H).

Enforced in code independently of any AI agent. AI output is never an
approved source of financial truth.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "SourceDecision",
    "SourceTier",
    "authoritative_eligibility",
    "classify_source",
    "is_ai_agent_source",
    "is_forbidden_vendor_source",
]


class SourceTier(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    AI_AGENT = "AI_AGENT"
    FORBIDDEN = "FORBIDDEN"
    UNKNOWN = "UNKNOWN"


class SourceDecision(StrEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    UNKNOWN = "UNKNOWN"


_PRIMARY = frozenset(
    {
        "nse",
        "bse",
        "company",
        "company_official_website",
        "company_ir",
        "company_annual_report",
        "company_quarterly_filing",
        "company_filing",
        "corporate_action_disclosure",
        "sebi",
        "mca",
        "rbi",
        "sector_regulator",
        "nsdl",
        "cdsl",
    }
)
_SECONDARY = frozenset({"ibef", "yahoo_finance", "yahoo"})
_AI_AGENTS = frozenset(
    {
        "gemini",
        "chatgpt",
        "claude",
        "deep_search",
        "openai",
        "anthropic",
        "google",
    }
)
_FORBIDDEN_VENDORS = frozenset(
    {"upstox", "fmp", "yfinance", "alpha_vantage", "alphavantage"}
)


def is_ai_agent_source(source: str) -> bool:
    return str(source or "").strip().lower() in _AI_AGENTS


def is_forbidden_vendor_source(source: str) -> bool:
    return str(source or "").strip().lower() in _FORBIDDEN_VENDORS


def classify_source(source: str) -> tuple[SourceTier, SourceDecision]:
    key = str(source or "").strip().lower()
    if not key:
        return SourceTier.UNKNOWN, SourceDecision.UNKNOWN
    if is_ai_agent_source(key):
        return SourceTier.AI_AGENT, SourceDecision.REJECT
    if is_forbidden_vendor_source(key):
        return SourceTier.FORBIDDEN, SourceDecision.REJECT
    if key in _PRIMARY:
        return SourceTier.PRIMARY, SourceDecision.ACCEPT
    if key in _SECONDARY:
        return SourceTier.SECONDARY, SourceDecision.UNKNOWN
    return SourceTier.UNKNOWN, SourceDecision.UNKNOWN


def authoritative_eligibility(source: str) -> SourceDecision:
    """Authoritative financial fields: PRIMARY eligible; all else rejected."""
    tier, decision = classify_source(source)
    if tier is SourceTier.PRIMARY and decision is SourceDecision.ACCEPT:
        return SourceDecision.ACCEPT
    return SourceDecision.REJECT
