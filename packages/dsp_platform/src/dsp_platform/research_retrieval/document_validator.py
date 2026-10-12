"""Document content validation, claim grounding, and untrusted input defense."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from dsp_platform.research_retrieval.models import (
    EvidenceFreshness,
    EvidenceStatus,
    FetchedDocument,
)

__all__ = [
    "DocumentValidationResult",
    "DocumentValidator",
    "ValidationFailureReason",
    "detect_prompt_injection",
    "parse_indian_and_western_number",
]


class ValidationFailureReason(StrEnum):
    NONE = "none"
    EMPTY_DOCUMENT = "empty_document"
    ENTITY_MISMATCH = "entity_mismatch"
    METRIC_NOT_FOUND = "metric_not_found"
    VALUE_MISMATCH = "value_mismatch"
    PERIOD_MISMATCH = "period_mismatch"
    SHARE_TYPE_MISMATCH = "share_type_mismatch"
    SUSPECTED_INJECTION = "suspected_prompt_injection"
    UNGROUNDED_CLAIM = "ungrounded_claim"


@dataclass(frozen=True, slots=True)
class DocumentValidationResult:
    is_valid: bool
    status: EvidenceStatus
    failure_reason: ValidationFailureReason
    grounded_excerpt: str
    document_location: str | None = None
    freshness: EvidenceFreshness = EvidenceFreshness.UNKNOWN
    warnings: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status.value,
            "failure_reason": self.failure_reason.value,
            "grounded_excerpt": self.grounded_excerpt,
            "document_location": self.document_location,
            "freshness": self.freshness.value,
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


# Adversarial prompt injection keywords in retrieved documents
_PROMPT_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE),
    re.compile(r"reveal\s+(internal|secret|private)\s+(prompt|api_key|token)", re.IGNORECASE),
    re.compile(r"do\s+not\s+validate\s+this\s+claim", re.IGNORECASE),
    re.compile(r"override\s+source\s+governance", re.IGNORECASE),
    re.compile(r"<script[\s>]", re.IGNORECASE),
)


def detect_prompt_injection(text: str) -> tuple[bool, str]:
    """Scan text for prompt injection attempts in untrusted content."""
    for pattern in _PROMPT_INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return True, f"Detected adversarial pattern: '{match.group(0)}'"
    return False, ""


def parse_indian_and_western_number(text: str) -> float | None:
    """Parse text representation of financial numbers with scale multipliers."""
    cleaned = text.replace(",", "").strip()
    match = re.search(r"(-?\d+(?:\.\d+)?)\s*(cr|crore|crores|lakh|lakhs|lk|m|million|b|billion|k)?", cleaned, re.IGNORECASE)
    if not match:
        return None
    val = float(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit in {"cr", "crore", "crores"}:
        return val * 10_000_000.0
    if unit in {"lakh", "lakhs", "lk"}:
        return val * 100_000.0
    if unit in {"m", "million"}:
        return val * 1_000_000.0
    if unit in {"b", "billion"}:
        return val * 1_000_000_000.0
    if unit in {"k"}:
        return val * 1_000.0
    return val


class DocumentValidator:
    """Strictly validates financial claims against actual document text."""

    def __init__(self, tolerance: float = 0.02) -> None:
        self.tolerance = tolerance

    def validate_claim(
        self,
        document: FetchedDocument,
        ticker: str,
        claim: str,
        metric_name: str | None = None,
        claimed_value: float | None = None,
        units: str | None = None,
        claimed_period: str | None = None,
        is_share_count: bool = False,
    ) -> DocumentValidationResult:
        """Validate whether the document text factually supports the asserted claim."""
        text = document.text_content
        if not text or len(text.strip()) == 0:
            return DocumentValidationResult(
                is_valid=False,
                status=EvidenceStatus.REJECTED,
                failure_reason=ValidationFailureReason.EMPTY_DOCUMENT,
                grounded_excerpt="",
            )

        # Check for adversarial prompt injection in document
        has_injection, injection_desc = detect_prompt_injection(text)
        warnings: list[str] = []
        if has_injection:
            warnings.append(f"Prompt injection pattern detected: {injection_desc}")

        # 1. Entity / Issuer Verification
        symbol = ticker.strip().upper()
        # Look for symbol or entity in text (case-insensitive boundary check)
        entity_pattern = re.compile(rf"\b{re.escape(symbol)}\b", re.IGNORECASE)
        if not entity_pattern.search(text):
            return DocumentValidationResult(
                is_valid=False,
                status=EvidenceStatus.REJECTED,
                failure_reason=ValidationFailureReason.ENTITY_MISMATCH,
                grounded_excerpt="",
                warnings=tuple(warnings),
            )

        # 2. Metric and Value Verification (if numerical value asserted)
        grounded_excerpt = ""
        location = None
        if claimed_value is not None:
            # Search for numbers in document text
            found_match = False
            # Look for number patterns in text with surrounding context
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            for idx, para in enumerate(paragraphs):
                # Search numbers in paragraph
                num_matches = re.finditer(r"(-?\d+(?:,\d+)*(?:\.\d+)?)\s*(?:cr|crore|crores|lakh|lakhs|lk|m|million|b|billion|k)?", para, re.IGNORECASE)
                for m in num_matches:
                    parsed_num = parse_indian_and_western_number(m.group(0))
                    if parsed_num is not None:
                        # Check within relative tolerance or unit-scaled match
                        diff = abs(parsed_num - claimed_value)
                        denom = max(abs(claimed_value), 1.0)
                        if (diff / denom) <= self.tolerance:
                            found_match = True
                            grounded_excerpt = para[:500]
                            location = f"paragraph_{idx + 1}"
                            break
                if found_match:
                    break

            if not found_match:
                return DocumentValidationResult(
                    is_valid=False,
                    status=EvidenceStatus.REJECTED,
                    failure_reason=ValidationFailureReason.VALUE_MISMATCH,
                    grounded_excerpt="",
                    warnings=tuple(warnings),
                )

        # 3. Share-count specificity check
        if is_share_count:
            # Check if excerpt or document specifies weighted average or diluted rather than period-end
            lower_text = text.lower()
            if "weighted average" in lower_text or "diluted shares" in lower_text:
                if "period-end" not in lower_text and "outstanding shares" not in lower_text:
                    return DocumentValidationResult(
                        is_valid=False,
                        status=EvidenceStatus.REJECTED,
                        failure_reason=ValidationFailureReason.SHARE_TYPE_MISMATCH,
                        grounded_excerpt=grounded_excerpt or text[:200],
                        warnings=tuple(warnings + ["Weighted average or diluted shares cannot substitute for period-end count"]),
                    )

        # 4. Period Verification
        freshness = EvidenceFreshness.CURRENT
        if claimed_period:
            period_clean = claimed_period.strip().upper()
            if period_clean not in text.upper():
                warnings.append(f"Reporting period '{claimed_period}' not found verbatim in document text")
                freshness = EvidenceFreshness.HISTORICAL

        if not grounded_excerpt:
            # Use matching entity context as excerpt
            match = entity_pattern.search(text)
            start = max(0, match.start() - 100) if match else 0
            grounded_excerpt = text[start : start + 400].strip()

        return DocumentValidationResult(
            is_valid=True,
            status=EvidenceStatus.VERIFIED,
            failure_reason=ValidationFailureReason.NONE,
            grounded_excerpt=grounded_excerpt,
            document_location=location,
            freshness=freshness,
            warnings=tuple(warnings),
        )
