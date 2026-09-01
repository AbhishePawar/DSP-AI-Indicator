"""Provider-neutral evaluation request/result schema.

Used for offline comparison of LLM candidates (DeepSeek, OpenAI, Gemini,
Anthropic) without changing the production research path. Evaluation
results carry cost + quality components; quality is left unfilled
(provider-supplied later) so this module does not invent scores.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from llm_adapters.model_catalog import ModelInfo, get_model_info


class EvaluationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ErrorCategory(str, Enum):
    NONE = "none"
    TIMEOUT = "timeout"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_FAILED = "provider_failed"
    RATE_LIMIT = "rate_limit"
    SCHEMA_FAILURE = "schema_failure"
    MALFORMED_OUTPUT = "malformed_output"
    INVALID_AI_OUTPUT = "invalid_ai_output"
    MISSING_EVIDENCE = "missing_evidence"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CITATION_FAILURE = "citation_failure"
    TOOL_FAILURE = "tool_failure"
    INVALID_TOOL_CALL = "invalid_tool_call"
    TOOL_UNAVAILABLE = "tool_unavailable"
    VALIDATION_FAILED = "validation_failed"
    LOOP_LIMIT_EXCEEDED = "loop_limit_exceeded"
    PRIVACY_VIOLATION = "privacy_violation"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    """One candidate-model evaluation request."""

    research_case_id: str
    research_spec_version: str
    model_identity: str
    input_evidence_ref: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Token accounting for a single evaluation run."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return int(self.input_tokens) + int(self.output_tokens)


@dataclass(frozen=True, slots=True)
class QualityEvaluation:
    """Schema for later evaluator-supplied quality scoring.

    All fields are 0.0-1.0 where applicable. None means "not yet scored".
    Composite quality_score is computed elsewhere from these.
    """

    factual_accuracy: float | None = None
    financial_reasoning: float | None = None
    valuation_reasoning: float | None = None
    buffett_reasoning: float | None = None
    moat_business_quality: float | None = None
    management: float | None = None
    financial_strength: float | None = None
    earnings_quality: float | None = None
    growth_quality: float | None = None
    risk: float | None = None
    evidence_correctness: float | None = None
    hallucination: float | None = None
    unsupported_claims: float | None = None
    structured_output: float | None = None
    consistency: float | None = None
    business_quality: float | None = None

    def component_values(self) -> tuple[float, ...]:
        """Return non-None components as a tuple (deterministic order)."""
        return tuple(
            v
            for v in (
                self.factual_accuracy,
                self.financial_reasoning,
                self.valuation_reasoning,
                self.buffett_reasoning,
                self.moat_business_quality,
                self.management,
                self.financial_strength,
                self.earnings_quality,
                self.growth_quality,
                self.risk,
                self.evidence_correctness,
                self.hallucination,
                self.unsupported_claims,
                self.structured_output,
                self.consistency,
                self.business_quality,
            )
            if v is not None
        )

    @property
    def is_empty(self) -> bool:
        return len(self.component_values()) == 0


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Outcome of one (request, model) evaluation run."""

    model: ModelInfo
    research_case_id: str
    status: EvaluationStatus
    latency_ms: int
    usage: TokenUsage
    estimated_cost_usd: float
    structured_output_valid: bool
    quality: QualityEvaluation
    error_category: ErrorCategory = ErrorCategory.NONE
    error_detail: str | None = None

    def is_success(self) -> bool:
        return self.status is EvaluationStatus.SUCCESS


__all__ = [
    "ErrorCategory",
    "EvaluationRequest",
    "EvaluationResult",
    "EvaluationStatus",
    "QualityEvaluation",
    "TokenUsage",
    "get_model_info",
]
