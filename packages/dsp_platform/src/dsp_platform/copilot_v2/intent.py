"""Intent routing for Copilot 2.0 — keyword classification only (no NLP model)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "COPILOT_MODES",
    "classify_intent",
    "extract_symbols",
]

COPILOT_MODES: tuple[str, ...] = (
    "chat",
    "company",
    "valuation",
    "committee",
    "risk",
    "portfolio",
    "comparison",
    "document",
    "memo",
    "scenarios",
    "buffett",
)

_SYMBOL_STOP = {
    "ANALYZE",
    "SUMMARIZE",
    "COMPARE",
    "VS",
    "VERSUS",
    "WHY",
    "WHAT",
    "EXPLAIN",
    "THE",
    "AND",
    "FOR",
    "MY",
    "IS",
    "IN",
    "OF",
    "A",
    "AN",
    "TO",
    "BANK",
    "LIKE",
    "BUFFETT",
}


def classify_intent(message: str, *, mode: str | None = None) -> str:
    """Return a Copilot 2.0 mode. Explicit mode wins; else keyword heuristics."""
    if mode and mode.strip().lower() in COPILOT_MODES:
        return mode.strip().lower()

    text = (message or "").strip().lower()
    if not text:
        return "chat"

    rules: list[tuple[str, tuple[str, ...]]] = [
        (
            "comparison",
            ("compare", " vs ", "versus", "against"),
        ),
        (
            "valuation",
            (
                "intrinsic",
                "dcf",
                "margin of safety",
                "mos",
                "buffett score",
                "fair value",
                "valuation",
            ),
        ),
        (
            "committee",
            (
                "bull case",
                "bear case",
                "base case",
                "committee",
                "voting",
                "minority",
            ),
        ),
        (
            "risk",
            (
                "risk score",
                "stress test",
                "monte carlo",
                "concentration",
                "diversification",
                "biggest risks",
            ),
        ),
        (
            "portfolio",
            ("portfolio", "holding", "overvalued", "diversify"),
        ),
        (
            "document",
            (
                "annual report",
                "transcript",
                "filing",
                "10-k",
                "10-q",
                "investor presentation",
                "sec ",
                "nse",
                "bse filing",
            ),
        ),
        (
            "memo",
            ("investment memo", "investment thesis", "catalyst"),
        ),
        (
            "scenarios",
            ("bull / base / bear", "scenario report", "scenario analysis"),
        ),
        (
            "buffett",
            ("explain like buffett", "like buffett", "plain language"),
        ),
        (
            "company",
            ("analyze ", "summarise ", "summarize ", "analyse "),
        ),
    ]
    for intent, needles in rules:
        if any(n in text for n in needles):
            return intent
    return "chat"


def extract_symbols(message: str, *, hinted: list[str] | None = None) -> list[str]:
    """Best-effort ticker extraction from message + hints (never fabricates quotes)."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in hinted or []:
        sym = str(raw or "").strip().upper()
        if sym and sym not in seen:
            seen.add(sym)
            out.append(sym)

    tokens = (message or "").replace(",", " ").replace("/", " ").split()
    for token in tokens:
        cleaned = "".join(ch for ch in token if ch.isalnum() or ch in {".", "-"})
        if not cleaned:
            continue
        upper = cleaned.upper()
        if upper in _SYMBOL_STOP:
            continue
        if upper.isalpha() and 1 <= len(upper) <= 6:
            if upper not in seen:
                seen.add(upper)
                out.append(upper)
    return out[:8]


def source_ref(engine: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "engine": engine,
        "detail": detail,
        "note": "Pass-through explanation only — no recalculation.",
    }
