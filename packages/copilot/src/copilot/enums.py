"""Enumerations for AI Copilot domain models (J1.0)."""

from __future__ import annotations

from enum import StrEnum

__all__ = [
    "ConfidenceLevel",
    "ConversationRole",
    "ConversationState",
    "ConversationStatus",
    "ExplanationStatus",
    "ExplanationType",
    "LanguageModelStatus",
    "ResponseStatus",
    "UserIntentType",
]


class ConversationState(StrEnum):
    """Conversation session lifecycle — never a market conclusion."""

    PENDING = "pending"
    ACTIVE = "active"
    CLARIFYING = "clarifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConversationStatus(StrEnum):
    """Conversation engine run completeness — not a market-quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    CLARIFY = "clarify"
    OUT_OF_SCOPE = "out_of_scope"
    FAILED = "failed"


class ConversationRole(StrEnum):
    """Turn speaker role — never a BUY/SELL/HOLD conclusion."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class UserIntentType(StrEnum):
    """Frozen intent taxonomy for routing — not a financial conclusion."""

    EXPLAIN_REPORT = "explain_report"
    NAVIGATE_GRAPH = "navigate_graph"
    SUMMARIZE_POSTURE = "summarize_posture"
    TRACE_EVIDENCE = "trace_evidence"
    COMPARE_OUTCOMES = "compare_outcomes"
    CLARIFY = "clarify"
    UNKNOWN = "unknown"
    OUT_OF_SCOPE = "out_of_scope"


class ExplanationType(StrEnum):
    """How an explanation was produced — distinguishes evidence vs narrative."""

    EVIDENCE_SUMMARY = "evidence_summary"
    NARRATIVE = "narrative"
    HYBRID = "hybrid"
    CLARIFICATION = "clarification"
    REFUSAL = "refusal"


class ExplanationStatus(StrEnum):
    """Explanation engine run completeness — not a market-quality score."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    REFUSED = "refused"
    CLARIFY = "clarify"
    EMPTY = "empty"
    FAILED = "failed"


class ConfidenceLevel(StrEnum):
    """Citation-coverage confidence — not a financial confidence score."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ResponseStatus(StrEnum):
    """Copilot response completeness — presentation only."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    EMPTY = "empty"
    FAILED = "failed"
    REFUSED = "refused"


class LanguageModelStatus(StrEnum):
    """Provider-neutral LM result status — no vendor enums."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    REFUSAL = "refusal"
    FAILED = "failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    UNKNOWN = "unknown"
