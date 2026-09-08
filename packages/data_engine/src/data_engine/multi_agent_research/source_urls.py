"""Source URL validation against the SIMPLE-14H whitelist.

An agent-supplied URL is not evidence. The host must match an allowed
organization class before a claim is eligible for reconciliation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from data_engine.source_policy import SourceDecision, SourceTier

__all__ = [
    "UrlClassification",
    "classify_source_url",
]


class UrlHostClass(StrEnum):
    PRIMARY_EXCHANGE = "PRIMARY_EXCHANGE"
    PRIMARY_REGULATOR = "PRIMARY_REGULATOR"
    PRIMARY_DEPOSITORY = "PRIMARY_DEPOSITORY"
    COMPANY_DECLARED = "COMPANY_DECLARED"
    SECONDARY = "SECONDARY"
    AI_AGENT = "AI_AGENT"
    FORBIDDEN = "FORBIDDEN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class UrlClassification:
    host: str
    host_class: UrlHostClass
    tier: SourceTier
    decision: SourceDecision
    https: bool
    detail: str


_EXCHANGE = frozenset(
    {
        "nseindia.com",
        "www.nseindia.com",
        "bseindia.com",
        "www.bseindia.com",
    }
)
_REGULATOR = frozenset(
    {
        "sebi.gov.in",
        "www.sebi.gov.in",
        "mca.gov.in",
        "www.mca.gov.in",
        "rbi.org.in",
        "www.rbi.org.in",
        "irdai.gov.in",
        "www.irdai.gov.in",
        "trai.gov.in",
        "www.trai.gov.in",
        "pngrb.gov.in",
        "www.pngrb.gov.in",
    }
)
_DEPOSITORY = frozenset(
    {
        "nsdl.co.in",
        "www.nsdl.co.in",
        "cdslindia.com",
        "www.cdslindia.com",
    }
)
_SECONDARY = frozenset(
    {
        "ibef.org",
        "www.ibef.org",
        "finance.yahoo.com",
        "yahoo.com",
        "www.yahoo.com",
    }
)
_AI = frozenset(
    {
        "gemini.google.com",
        "generativelanguage.googleapis.com",
        "openai.com",
        "api.openai.com",
        "chatgpt.com",
        "anthropic.com",
        "api.anthropic.com",
        "claude.ai",
    }
)
_FORBIDDEN = frozenset(
    {
        "upstox.com",
        "www.upstox.com",
        "financialmodelingprep.com",
    }
)


def classify_source_url(
    url: str,
    *,
    declared_source_type: str = "",
) -> UrlClassification:
    raw = str(url or "").strip()
    if not raw:
        return UrlClassification(
            host="",
            host_class=UrlHostClass.UNKNOWN,
            tier=SourceTier.UNKNOWN,
            decision=SourceDecision.REJECT,
            https=False,
            detail="missing source_url",
        )
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower().rstrip(".")
    https = parsed.scheme.lower() == "https"
    if not host:
        return UrlClassification(
            host="",
            host_class=UrlHostClass.UNKNOWN,
            tier=SourceTier.UNKNOWN,
            decision=SourceDecision.REJECT,
            https=https,
            detail="unparseable source_url",
        )
    if host in _FORBIDDEN or host.endswith(".upstox.com"):
        return UrlClassification(
            host=host,
            host_class=UrlHostClass.FORBIDDEN,
            tier=SourceTier.FORBIDDEN,
            decision=SourceDecision.REJECT,
            https=https,
            detail="forbidden vendor host",
        )
    if host in _AI:
        return UrlClassification(
            host=host,
            host_class=UrlHostClass.AI_AGENT,
            tier=SourceTier.AI_AGENT,
            decision=SourceDecision.REJECT,
            https=https,
            detail="AI host cannot be an authoritative source",
        )
    if host in _EXCHANGE:
        return UrlClassification(
            host=host,
            host_class=UrlHostClass.PRIMARY_EXCHANGE,
            tier=SourceTier.PRIMARY,
            decision=SourceDecision.ACCEPT if https else SourceDecision.UNKNOWN,
            https=https,
            detail="exchange host",
        )
    if host in _REGULATOR:
        return UrlClassification(
            host=host,
            host_class=UrlHostClass.PRIMARY_REGULATOR,
            tier=SourceTier.PRIMARY,
            decision=SourceDecision.ACCEPT if https else SourceDecision.UNKNOWN,
            https=https,
            detail="regulator host",
        )
    if host in _DEPOSITORY:
        return UrlClassification(
            host=host,
            host_class=UrlHostClass.PRIMARY_DEPOSITORY,
            tier=SourceTier.PRIMARY,
            decision=SourceDecision.ACCEPT if https else SourceDecision.UNKNOWN,
            https=https,
            detail="depository host",
        )
    if host in _SECONDARY:
        return UrlClassification(
            host=host,
            host_class=UrlHostClass.SECONDARY,
            tier=SourceTier.SECONDARY,
            decision=SourceDecision.UNKNOWN,
            https=https,
            detail="secondary research host; not authoritative financial truth",
        )
    declared = str(declared_source_type or "").strip().lower()
    if declared.startswith("company") and https:
        return UrlClassification(
            host=host,
            host_class=UrlHostClass.COMPANY_DECLARED,
            tier=SourceTier.PRIMARY,
            decision=SourceDecision.UNKNOWN,
            https=https,
            detail="declared company IR host; organization not independently bound",
        )
    return UrlClassification(
        host=host,
        host_class=UrlHostClass.UNKNOWN,
        tier=SourceTier.UNKNOWN,
        decision=SourceDecision.REJECT,
        https=https,
        detail="host not on the approved whitelist",
    )
