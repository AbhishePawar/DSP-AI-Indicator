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
    "claim_terms",
    "metric_terms",
    "parse_indian_and_western_number",
    "period_present",
    "unit_multiplier",
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


_UNIT_MULTIPLIERS = {
    "cr": 10_000_000.0, "crore": 10_000_000.0, "crores": 10_000_000.0,
    "lakh": 100_000.0, "lakhs": 100_000.0, "lk": 100_000.0,
    "m": 1_000_000.0, "mn": 1_000_000.0, "million": 1_000_000.0, "millions": 1_000_000.0,
    "b": 1_000_000_000.0, "bn": 1_000_000_000.0, "billion": 1_000_000_000.0, "billions": 1_000_000_000.0,
    "k": 1_000.0, "thousand": 1_000.0, "thousands": 1_000.0,
}

_CLAIM_STOPWORDS = frozenset(
    {
        "that",
        "this",
        "with",
        "from",
        "were",
        "have",
        "has",
        "had",
        "will",
        "been",
        "into",
        "over",
        "than",
        "their",
        "there",
        "which",
        "about",
        "after",
        "before",
        "during",
        "under",
        "above",
        "below",
        "between",
        "company",
        "limited",
        "ltd",
        "reported",
        "report",
        "reports",
        "year",
    }
)

# Characters on either side of a matched number that may hold the metric label.
_METRIC_WINDOW = 80


def unit_multiplier(units: str | None) -> float:
    """Scale implied by a units label such as 'INR crore' or 'millions'. Unknown labels scale by 1."""
    if not units:
        return 1.0
    for token in re.findall(r"[a-z]+", units.lower()):
        if token in _UNIT_MULTIPLIERS:
            return _UNIT_MULTIPLIERS[token]
    return 1.0


def metric_terms(metric_name: str | None) -> tuple[str, ...]:
    """Split a metric label like 'NET_PROFIT' into the words that must appear beside the value."""
    if not metric_name:
        return ()
    return tuple(t for t in re.split(r"[^a-z0-9]+", metric_name.lower()) if t)


def _normalize_period(text: str) -> str:
    return re.sub(r"[\s\-'’/]", "", text.upper())


def period_present(claimed_period: str, text: str) -> bool:
    """True when the claimed period (e.g. FY2026, FY 2025-26, FY26, Q1FY26) occurs in the text."""
    norm_text = _normalize_period(text)
    period = _normalize_period(claimed_period)
    if not period:
        return True
    candidates = {period}
    full_year = re.fullmatch(r"(Q[1-4])?FY(\d{4})", period)
    if full_year:
        quarter, year = full_year.group(1) or "", int(full_year.group(2))
        candidates |= {f"{quarter}FY{year % 100:02d}", f"{quarter}FY{year - 1}{year % 100:02d}", f"{quarter}FY{year - 1}{year}"}
    return any(c in norm_text for c in candidates)


def claim_terms(claim: str, ticker: str) -> tuple[str, ...]:
    """Content words of a prose claim that the document must contain to ground it."""
    symbol = ticker.strip().lower()
    words = re.findall(r"[a-z][a-z0-9]+", claim.lower())
    return tuple(w for w in words if len(w) >= 4 and w not in _CLAIM_STOPWORDS and w != symbol)


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

        # 2. Metric, Units and Value Verification (if numerical value asserted)
        grounded_excerpt = ""
        location = None
        lower_full = text.lower()
        terms = metric_terms(metric_name)
        if terms and not all(t in lower_full for t in terms):
            return DocumentValidationResult(
                is_valid=False,
                status=EvidenceStatus.REJECTED,
                failure_reason=ValidationFailureReason.METRIC_NOT_FOUND,
                grounded_excerpt="",
                warnings=tuple(warnings),
            )
        if claimed_value is not None:
            # A claim expressed "in crore" etc. is compared in absolute terms.
            target = claimed_value * unit_multiplier(units)
            found_match = False
            value_seen = False
            paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
            for idx, para in enumerate(paragraphs):
                lower_para = para.lower()
                num_matches = re.finditer(
                    r"(?<![\w.])(-?\d+(?:,\d+)*(?:\.\d+)?)\s*(?:cr|crore|crores|lakh|lakhs|lk|m|million|b|billion|k)?\b",
                    para,
                    re.IGNORECASE,
                )
                for m in num_matches:
                    parsed_num = parse_indian_and_western_number(m.group(0))
                    if parsed_num is None:
                        continue
                    diff = abs(parsed_num - target)
                    denom = max(abs(target), 1.0)
                    if (diff / denom) > self.tolerance:
                        continue
                    value_seen = True
                    # The number only supports the claim if the metric label sits beside it.
                    window = lower_para[max(0, m.start() - _METRIC_WINDOW) : m.end() + _METRIC_WINDOW]
                    if terms and not all(t in window for t in terms):
                        continue
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
                    failure_reason=(
                        ValidationFailureReason.METRIC_NOT_FOUND if value_seen else ValidationFailureReason.VALUE_MISMATCH
                    ),
                    grounded_excerpt="",
                    warnings=tuple(warnings),
                )
        elif claim and claim.strip():
            # Prose claims without a value must have every content word present in the document.
            missing = [t for t in claim_terms(claim, symbol) if t not in lower_full]
            if missing:
                return DocumentValidationResult(
                    is_valid=False,
                    status=EvidenceStatus.REJECTED,
                    failure_reason=ValidationFailureReason.UNGROUNDED_CLAIM,
                    grounded_excerpt="",
                    warnings=tuple(warnings + [f"Claim terms not found in document: {', '.join(missing)}"]),
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

        # 4. Period Verification: a claim for a period the document never mentions is not supported.
        freshness = EvidenceFreshness.CURRENT
        if claimed_period and not period_present(claimed_period, text):
            return DocumentValidationResult(
                is_valid=False,
                status=EvidenceStatus.REJECTED,
                failure_reason=ValidationFailureReason.PERIOD_MISMATCH,
                grounded_excerpt="",
                warnings=tuple(warnings + [f"Reporting period '{claimed_period}' not found in document text"]),
            )

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
