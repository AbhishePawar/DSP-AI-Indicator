"""Prompt-injection defense: retrieved documents are DATA, never instructions."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["InjectionScan", "scan_untrusted_text"]

_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard previous",
    "you are now",
    "new system prompt",
    "change system rules",
    "override source policy",
    "promote this number",
    "use this number as verified",
    "call this url",
    "execute the following",
    "wget ",
    "curl ",
)


@dataclass(frozen=True, slots=True)
class InjectionScan:
    suspect: bool
    matched: tuple[str, ...]
    treated_as: str = "DATA"


def scan_untrusted_text(text: str | None) -> InjectionScan:
    blob = str(text or "").lower()
    matched = tuple(p for p in _PATTERNS if p in blob)
    return InjectionScan(suspect=bool(matched), matched=matched, treated_as="DATA")
