"""Typed research failures. Domain outcomes, not generic exceptions."""

from __future__ import annotations

__all__ = [
    "DOMAIN_FAILURE_CODES",
    "RESEARCH_FAILURE_CODES",
    "TRANSPORT_FAILURE_CODES",
    "ResearchFailure",
    "is_transport_failure",
    "map_retrieval_to_failure_code",
    "classify_openai_failure",
]

TRANSPORT_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "NETWORK",
        "HTTP",
        "AUTH",
        "RATE_LIMIT",
        "MCP_UNAVAILABLE",
        "MCP_TIMEOUT",
        "MCP_PROTOCOL_ERROR",
        "MCP_RATE_LIMITED",
        "MCP_AUTH_REQUIRED",
        "OPENAI_UNAVAILABLE",
        "OPENAI_TIMEOUT",
        "OPENAI_RATE_LIMITED",
        "NSE_UNAVAILABLE",
        "NSE_TIMEOUT",
    }
)

DOMAIN_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "SECURITY_UNKNOWN",
        "SECURITY_NOT_FOUND",
        "SECURITY_AMBIGUOUS",
        "SOURCE_UNAVAILABLE",
        "DOCUMENT_NOT_FOUND",
        "DOCUMENT_INVALID",
        "DOCUMENT_WRONG_IDENTITY",
        "STATEMENT_NOT_FOUND",
        "UNIT_UNKNOWN",
        "PERIOD_UNKNOWN",
        "BASIS_UNKNOWN",
        "COLUMN_AMBIGUOUS",
        "ROW_AMBIGUOUS",
        "SEMANTIC_AMBIGUITY",
        "SHARE_COUNT_NOT_CURRENT",
        "CORPORATE_ACTION_UNRESOLVED",
        "SOURCE_CONFLICT",
        "EVIDENCE_STALE",
        "CAPABILITY_UNAVAILABLE",
        "PRIMARY_SOURCE_UNAVAILABLE",
        "DISCOVERY_REQUIRED",
        "MCP_TOOL_NOT_FOUND",
        "MCP_INVALID_ARGUMENT",
        "MCP_MALFORMED_RESPONSE",
        "DATA_STALE",
        "DATA_VALIDATION_FAILED",
        "EXTRACTION_FAILURE",
        "IDENTITY_FAILURE",
        "SEMANTIC_FAILURE",
        "FRESHNESS_FAILURE",
        "RECONCILIATION_CONFLICT",
        "UNSUPPORTED_SECURITY",
        "MISSING_REQUIRED_DATA",
        "MCP_TOOL_ERROR",
        "EVIDENCE_MISSING",
        "EVIDENCE_CONFLICT",
        "NORMALIZATION_FAILURE",
    }
)

RESEARCH_FAILURE_CODES: frozenset[str] = TRANSPORT_FAILURE_CODES | DOMAIN_FAILURE_CODES


def is_transport_failure(code: str) -> bool:
    """Provider/network errors trip breakers. Domain/data errors do not."""
    return code in TRANSPORT_FAILURE_CODES


def map_retrieval_to_failure_code(reason: str, http_status: int | None = None) -> str:
    """Map a retrieval reason onto the typed taxonomy. Never invent a value."""
    lowered = str(reason or "").lower()
    if http_status in {401, 403} or "http 403" in lowered or "unauthorized" in lowered:
        return "AUTH"
    if http_status == 429 or "http 429" in lowered or "rate limit" in lowered:
        return "RATE_LIMIT"
    if http_status == 404 or "http 404" in lowered or "not found" in lowered:
        return "DOCUMENT_NOT_FOUND"
    if http_status is not None and http_status >= 400:
        return "HTTP"
    if any(
        token in lowered
        for token in ("timeout", "timed out", "dns", "getaddrinfo", "ssl", "tls", "connection")
    ):
        return "NETWORK"
    if "empty document" in lowered or "invalid pdf" in lowered or "no text layer" in lowered:
        return "EXTRACTION_FAILURE"
    return "SOURCE_UNAVAILABLE"


def classify_openai_failure(status: str, http_status: int | None = None) -> str:
    """OpenAI transport errors. Domain/data failures must not use these codes."""
    text = str(status or "").strip().lower()
    if http_status == 429 or "rate" in text:
        return "OPENAI_RATE_LIMITED"
    if "timeout" in text:
        return "OPENAI_TIMEOUT"
    return "OPENAI_UNAVAILABLE"


class ResearchFailure(Exception):
    """Typed research/MCP failure. Transport vs domain is classified by code."""

    def __init__(self, code: str, detail: str, field: str | None = None) -> None:
        if code not in RESEARCH_FAILURE_CODES:
            raise ValueError(f"unknown research failure {code!r}")
        self.code = code
        self.detail = detail
        self.field = field
        super().__init__(f"{code}: {detail}")
