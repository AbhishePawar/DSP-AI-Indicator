"""Stable evidence identity. AI interpretation is not a second primary source."""

from __future__ import annotations

import hashlib

from data_engine.official_research.models import EvidenceItem

__all__ = [
    "IDENTITY_AMBIGUOUS",
    "IDENTITY_MISMATCH",
    "IDENTITY_UNKNOWN",
    "IDENTITY_VERIFIED",
    "classify_security_identity",
    "dedupe_evidence",
    "evidence_fingerprint",
    "identities_comparable",
]

IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
IDENTITY_UNKNOWN = "IDENTITY_UNKNOWN"


def evidence_fingerprint(item: EvidenceItem) -> str:
    """Identity of the underlying source fact, not the researching agent."""
    source = (item.source_url or item.source or "").strip().lower()
    payload = "|".join(
        (
            item.isin.strip().upper(),
            item.mic.strip().upper(),
            item.field.strip(),
            "" if item.as_of is None else item.as_of.isoformat(),
            str(item.value or ""),
            source,
            (item.document_hash or "").strip(),
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dedupe_evidence(items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
    """Keep one row per source fact. Prefer primary tool output over AI narrative."""
    ranked: dict[str, EvidenceItem] = {}
    order: list[str] = []
    for item in items:
        key = evidence_fingerprint(item)
        if key not in ranked:
            ranked[key] = item
            order.append(key)
            continue
        current = ranked[key]
        if _ai_row(current) and not _ai_row(item):
            ranked[key] = item
        elif not _ai_row(current) and _ai_row(item):
            continue
    return tuple(ranked[key] for key in order)


def _ai_row(item: EvidenceItem) -> bool:
    return item.source_type in {"llm", "agent_claim"} or item.agent in {
        "gemini_find",
        "chatgpt_verify",
        "claude_review",
        "openai_nse_mcp",
        "deep_search_attack",
    }


def classify_security_identity(
    item: EvidenceItem,
    *,
    expected_isin: str | None = None,
    expected_mic: str | None = None,
    expected_ticker: str | None = None,
) -> str:
    """Canonical identity is ISIN + MIC. Ticker or name alone is insufficient."""
    isin = str(item.isin or "").strip().upper()
    mic = str(item.mic or "").strip().upper()
    ticker = str(item.ticker or "").strip().upper()
    want_isin = str(expected_isin or "").strip().upper()
    want_mic = str(expected_mic or "").strip().upper()
    want_ticker = str(expected_ticker or "").strip().upper()
    if not isin and not mic:
        if ticker or str(item.company or "").strip():
            return IDENTITY_AMBIGUOUS
        return IDENTITY_UNKNOWN
    if not isin or not mic:
        return IDENTITY_AMBIGUOUS
    if want_isin and isin != want_isin:
        return IDENTITY_MISMATCH
    if want_mic and mic != want_mic:
        return IDENTITY_MISMATCH
    if want_isin and want_ticker and ticker and ticker != want_ticker:
        return IDENTITY_MISMATCH
    if item.identity_status == "FAIL":
        return IDENTITY_MISMATCH
    return IDENTITY_VERIFIED


def identities_comparable(left: EvidenceItem, right: EvidenceItem) -> bool:
    left_isin = str(left.isin or "").strip().upper()
    left_mic = str(left.mic or "").strip().upper()
    right_isin = str(right.isin or "").strip().upper()
    right_mic = str(right.mic or "").strip().upper()
    if not left_isin or not left_mic or not right_isin or not right_mic:
        return False
    return left_isin == right_isin and left_mic == right_mic
