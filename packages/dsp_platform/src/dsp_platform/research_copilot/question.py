"""Question processor (EPIC-A001) — deterministic topic mapping only."""

from __future__ import annotations

import re

from dsp_platform.research_copilot.models import ProcessedQuestion

__all__ = ["process_question"]

# Topic → keyword cues (deterministic; no ML)
_TOPIC_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("market_data", ("price", "market", "quote", "volume", "market cap", "trading")),
    ("valuation", ("valuation", "intrinsic", "fair value", "dcf", "value")),
    (
        "margin_of_safety",
        ("margin of safety", "mos", "upside", "downside", "safety margin"),
    ),
    ("business_quality", ("quality", "moat", "management", "governance")),
    ("risk", ("risk", "risks", "threat")),
    ("scenarios", ("scenario", "bull", "bear", "base case", "cagr")),
    ("recommendation", ("recommendation", "recommend", "rating", "stance")),
    ("financial_statements", ("financial", "statement", "income", "balance", "cash flow", "roe")),
    ("corporate_actions", ("corporate action", "dividend", "split", "buyback")),
    ("historical", ("historical", "history", "time series", "trend")),
    ("explainability", ("explain", "why", "how calculated", "formula", "inputs")),
    ("audit", ("audit", "provenance", "source", "version", "timestamp")),
    ("identity", ("company", "ticker", "identity", "exchange", "sector")),
    ("diff", ("diff", "difference", "changed", "compare", "comparison", "delta")),
    ("overview", ("summary", "overview", "executive", "header", "overall")),
)


def process_question(question: str) -> ProcessedQuestion:
    raw = question if isinstance(question, str) else str(question or "")
    normalized = re.sub(r"\s+", " ", raw.strip().lower())
    topics: list[str] = []
    for topic, keys in _TOPIC_KEYWORDS:
        if any(k in normalized for k in keys):
            topics.append(topic)
    if not topics:
        topics = ["overview"]
    # Stable unique order as defined above
    order = [t for t, _ in _TOPIC_KEYWORDS]
    topics_u = tuple(t for t in order if t in topics)
    intent = topics_u[0] if topics_u else "overview"
    return ProcessedQuestion(
        raw=raw.strip(),
        normalized=normalized,
        topics=topics_u,
        intent=intent,
    )
