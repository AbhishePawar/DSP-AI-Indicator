"""Prompt-injection defense: filings are documents, never instructions."""

from __future__ import annotations

import re

__all__ = ["looks_like_injection", "sanitize_document_text", "treat_as_document"]

_INJECTION = re.compile(
    r"(ignore (all )?(previous|prior) instructions|you are now|system prompt|"
    r"override (the )?policy|execute (this )?code|change evidence status|"
    r"set status to verified|write production|change provider|"
    r"set provider|ignore previous|override authority|change source policy|"
    r"rewrite verification rules|ignore the evidence judge|"
    r"rewrite (the )?dcf formula|change assumption bounds|override (the )?wacc|"
    r"set intrinsic value|rewrite calculation formulas|change (the )?weights)",
    re.IGNORECASE,
)


def treat_as_document(text: str) -> str:
    """Return document text unchanged as data. Never execute it."""
    return str(text or "")


def sanitize_document_text(text: str) -> str:
    """Keep extractable facts; neutralize instruction-like spans as quoted data."""
    raw = treat_as_document(text)
    return _INJECTION.sub("[document-text]", raw)


def looks_like_injection(text: str) -> bool:
    return bool(_INJECTION.search(str(text or "")))
