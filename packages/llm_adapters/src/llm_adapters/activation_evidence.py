"""Evidence bundle for the production AI activation guard.

The guard requires concrete, private evidence that DSP has actually
verified each precondition. This module is the typed shape of that
evidence — nothing here is ever serialized to a client.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from llm_adapters.evaluation import QualityEvaluation


@dataclass(frozen=True, slots=True)
class BenchmarkEvidence:
    """Evidence that a real benchmark has been completed."""

    benchmark_completed: bool
    benchmark_version: str
    case_count: int
    accepted_run_count: int
    best_overall_score: float
    best_model_identity: str
    cost_min_usd: float | None
    cost_max_usd: float | None

    @classmethod
    def empty(cls) -> "BenchmarkEvidence":
        return cls(
            benchmark_completed=False,
            benchmark_version="",
            case_count=0,
            accepted_run_count=0,
            best_overall_score=0.0,
            best_model_identity="",
            cost_min_usd=None,
            cost_max_usd=None,
        )


@dataclass(frozen=True, slots=True)
class ModelEvaluationEvidence:
    """Evidence for a single successful real model evaluation."""

    model_identity: str
    research_case_id: str
    quality: QualityEvaluation
    quality_score: float
    estimated_cost_usd: float
    pricing_known: bool
    structured_output_valid: bool
    token_usage: Mapping[str, int]
    latency_ms: int


@dataclass(frozen=True, slots=True)
class ConfigurationEvidence:
    """Evidence that the AI configuration itself is valid."""

    default_provider: str
    cost_efficient_model: str
    premium_model: str
    available_providers: tuple[str, ...]
    pricing_known_for_all_tiers: bool
    routing_tier_count: int
    all_provider_keys_configured: bool


@dataclass(frozen=True, slots=True)
class ToolEvidence:
    """Evidence that the DSP trusted tools are wired and reachable."""

    available_tools: tuple[str, ...]
    minimum_tool_count: int
    all_tools_healthy: bool


@dataclass(frozen=True, slots=True)
class PrivacyEvidence:
    """Evidence that the privacy boundary is intact."""

    private_fields_enumerated: bool
    public_pack_present: bool
    leakage_guard_active: bool
    benchmark_report_audited: bool


@dataclass(frozen=True, slots=True)
class FailClosedEvidence:
    """Evidence that fail-closed behaviour is wired and tested."""

    quality_gate_present: bool
    no_fabrication_guarantee: bool
    deterministic_fallback_present: bool
    escalation_present: bool


@dataclass(frozen=True, slots=True)
class ActivationEvidence:
    """Top-level evidence bundle presented to the activation guard."""

    benchmark: BenchmarkEvidence
    successful_evaluations: tuple[ModelEvaluationEvidence, ...]
    configuration: ConfigurationEvidence
    tools: ToolEvidence
    privacy: PrivacyEvidence
    fail_closed: FailClosedEvidence
    required_quality_threshold: float
    structured_output_required: bool = True
    notes: Mapping[str, str] = field(default_factory=dict)

    @classmethod
    def missing(cls) -> ActivationEvidence:
        """Fail-closed bundle when production has not supplied evidence.

        ``evaluate_activation`` must treat this as BLOCKED. This is not a
        second gate — it is the empty input the existing guard already
        rejects.
        """
        return cls(
            benchmark=BenchmarkEvidence.empty(),
            successful_evaluations=(),
            configuration=ConfigurationEvidence(
                default_provider="",
                cost_efficient_model="",
                premium_model="",
                available_providers=(),
                pricing_known_for_all_tiers=False,
                routing_tier_count=0,
                all_provider_keys_configured=False,
            ),
            tools=ToolEvidence(
                available_tools=(),
                minimum_tool_count=1,
                all_tools_healthy=False,
            ),
            privacy=PrivacyEvidence(
                private_fields_enumerated=False,
                public_pack_present=False,
                leakage_guard_active=False,
                benchmark_report_audited=False,
            ),
            fail_closed=FailClosedEvidence(
                quality_gate_present=False,
                no_fabrication_guarantee=False,
                deterministic_fallback_present=False,
                escalation_present=False,
            ),
            required_quality_threshold=60.0,
            structured_output_required=True,
        )


__all__ = [
    "ActivationEvidence",
    "BenchmarkEvidence",
    "ConfigurationEvidence",
    "FailClosedEvidence",
    "ModelEvaluationEvidence",
    "PrivacyEvidence",
    "ToolEvidence",
]
