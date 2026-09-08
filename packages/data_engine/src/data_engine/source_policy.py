"""Approved-source whitelist for future research (SIMPLE-14G boundary).

Enforced independently of any AI agent. AI output is never an approved
source of financial truth.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "SourceDecision",
    "SourceTier",
    "classify_source",
    "is_ai_agent_source",
]


class SourceTier(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
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
        "company_ir",
        "company_annual_report",
        "company_quarterly_filing",
        "sebi",
        "mca",
        "rbi",
        "nsdl",
        "cdsl",
    }
)
_SECONDARY = frozenset({"ibef", "yahoo_finance"})
_AI_AGENTS = frozenset(
    {"gemini", "chatgpt", "claude", "deep_search", "openai", "anthropic"}
)


def is_ai_agent_source(source: str) -> bool:
    return str(source or "").strip().lower() in _AI_AGENTS


def classify_source(source: str) -> tuple[SourceTier, SourceDecision]:
    key = str(source or "").strip().lower()
    if not key:
        return SourceTier.UNKNOWN, SourceDecision.UNKNOWN
    if is_ai_agent_source(key) or key in {"upstox", "fmp", "yfinance", "alpha_vantage"}:
        return SourceTier.FORBIDDEN, SourceDecision.REJECT
    if key in _PRIMARY:
        return SourceTier.PRIMARY, SourceDecision.ACCEPT
    if key in _SECONDARY:
        return SourceTier.SECONDARY, SourceDecision.UNKNOWN
    return SourceTier.UNKNOWN, SourceDecision.UNKNOWN
