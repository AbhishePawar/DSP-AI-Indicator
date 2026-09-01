"""Production AI activation guard.

The guard is the single server-side check that decides whether AI is
allowed to participate in production research. It is intentionally
fail-closed:

- missing evidence  -> BLOCKED
- malformed evidence -> BLOCKED
- threshold not met  -> BLOCKED
- pricing unknown    -> BLOCKED
- privacy guard off  -> BLOCKED
- fail-closed wiring missing -> BLOCKED

The verdict carries an internal reason list for operator telemetry.
Public callers receive ONLY the verdict state (READY / BLOCKED).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from llm_adapters.activation_evidence import (
    ActivationEvidence,
    BenchmarkEvidence,
    ConfigurationEvidence,
    FailClosedEvidence,
    ModelEvaluationEvidence,
    PrivacyEvidence,
    ToolEvidence,
)


class ActivationState(str, Enum):
    AI_PRODUCTION_READY = "ai_production_ready"
    AI_PRODUCTION_BLOCKED = "ai_production_blocked"


class ActivationCondition(str, Enum):
    """The 10 explicit gate conditions.

    Names are stable so the operator can grep for "benchmark_required",
    "quality_threshold_required", etc. in logs.
    """

    BENCHMARK_REQUIRED = "benchmark_required"
    SUCCESSFUL_MODEL_REQUIRED = "successful_model_required"
    QUALITY_THRESHOLD_REQUIRED = "quality_threshold_required"
    PRICING_KNOWN_REQUIRED = "pricing_known_required"
    STRUCTURED_OUTPUT_REQUIRED = "structured_output_required"
    DSP_TOOLS_AVAILABLE_REQUIRED = "dsp_tools_available_required"
    EVIDENCE_REQUIREMENTS_MET = "evidence_requirements_met"
    PRIVACY_BOUNDARY_REQUIRED = "privacy_boundary_required"
    FAIL_CLOSED_REQUIRED = "fail_closed_required"
    CONFIGURATION_VALID = "configuration_valid"


@dataclass(frozen=True, slots=True)
class ActivationVerdict:
    """Private verdict — never serialized to clients in full."""

    state: ActivationState
    passed: tuple[ActivationCondition, ...]
    failed: tuple[ActivationCondition, ...]
    reasons: tuple[str, ...]
    recommended_models: tuple[str, ...]

    def is_ready(self) -> bool:
        return self.state is ActivationState.AI_PRODUCTION_READY

    def public_state(self) -> str:
        """Return ONLY the public state string. No reasons, no internals."""
        return self.state.value


def _require(condition: ActivationCondition, ok: bool, reasons: list[str], msg: str) -> bool:
    if ok:
        reasons.append(f"ok:{condition.value}")
        return True
    reasons.append(f"FAIL:{condition.value}: {msg}")
    return False


def evaluate_activation(evidence: ActivationEvidence) -> ActivationVerdict:
    """Deterministic, fail-closed gate. All conditions are mandatory.

    Returns AI_PRODUCTION_READY only when every condition passes. The
    caller MUST treat AI_PRODUCTION_BLOCKED as "do not invoke AI".
    """
    reasons: list[str] = []
    passed: list[ActivationCondition] = []
    failed: list[ActivationCondition] = []

    def check(condition: ActivationCondition, ok: bool, msg: str) -> None:
        if _require(condition, ok, reasons, msg):
            passed.append(condition)
        else:
            failed.append(condition)

    # 1. Real benchmark completed
    check(
        ActivationCondition.BENCHMARK_REQUIRED,
        evidence.benchmark.benchmark_completed
        and evidence.benchmark.case_count > 0
        and evidence.benchmark.benchmark_version != "",
        "no real benchmark run; run packages.llm_adapters.benchmark_harness first",
    )

    # 2. At least one successful real model evaluation
    accepted_evals = [e for e in evidence.successful_evaluations if e.quality_score > 0]
    check(
        ActivationCondition.SUCCESSFUL_MODEL_REQUIRED,
        len(accepted_evals) > 0,
        "no successful model evaluation in the supplied evidence",
    )

    # 3. Required quality threshold is satisfied by every accepted run
    below = [e for e in accepted_evals if e.quality_score < evidence.required_quality_threshold]
    check(
        ActivationCondition.QUALITY_THRESHOLD_REQUIRED,
        len(below) == 0,
        f"{len(below)} accepted run(s) below threshold {evidence.required_quality_threshold:.2f}",
    )

    # 4. Provider pricing is known for every accepted run
    unknown_pricing = [e for e in accepted_evals if not e.pricing_known]
    check(
        ActivationCondition.PRICING_KNOWN_REQUIRED,
        len(unknown_pricing) == 0 and evidence.configuration.pricing_known_for_all_tiers,
        f"{len(unknown_pricing)} accepted run(s) have unknown pricing",
    )

    # 5. Structured output validation passes
    if evidence.structured_output_required:
        bad_struct = [e for e in accepted_evals if not e.structured_output_valid]
        check(
            ActivationCondition.STRUCTURED_OUTPUT_REQUIRED,
            len(bad_struct) == 0,
            f"{len(bad_struct)} accepted run(s) have invalid structured output",
        )
    else:
        passed.append(ActivationCondition.STRUCTURED_OUTPUT_REQUIRED)
        reasons.append("ok:structured_output_required (not required by policy)")

    # 6. DSP trusted tools are available
    check(
        ActivationCondition.DSP_TOOLS_AVAILABLE_REQUIRED,
        evidence.tools.all_tools_healthy
        and len(evidence.tools.available_tools) >= evidence.tools.minimum_tool_count,
        f"tools unhealthy or below minimum ({len(evidence.tools.available_tools)} of "
        f"{evidence.tools.minimum_tool_count} required)",
    )

    # 7. Evidence requirements satisfied (successful-eval non-empty, every
    #    required field populated). A cheap structural check on the bundle.
    evidence_complete = (
        evidence.benchmark.benchmark_version != ""
        and evidence.successful_evaluations
        and evidence.configuration.default_provider != ""
        and evidence.configuration.cost_efficient_model != ""
        and evidence.configuration.premium_model != ""
    )
    check(
        ActivationCondition.EVIDENCE_REQUIREMENTS_MET,
        evidence_complete,
        "evidence bundle is missing required fields",
    )

    # 8. Privacy boundary passes
    check(
        ActivationCondition.PRIVACY_BOUNDARY_REQUIRED,
        evidence.privacy.private_fields_enumerated
        and evidence.privacy.public_pack_present
        and evidence.privacy.leakage_guard_active
        and evidence.privacy.benchmark_report_audited,
        "privacy boundary is not fully verified",
    )

    # 9. Fail-closed behaviour passes
    check(
        ActivationCondition.FAIL_CLOSED_REQUIRED,
        evidence.fail_closed.quality_gate_present
        and evidence.fail_closed.no_fabrication_guarantee
        and evidence.fail_closed.deterministic_fallback_present
        and evidence.fail_closed.escalation_present,
        "fail-closed wiring is incomplete",
    )

    # 10. Configuration is valid
    valid_providers = {
        "openai", "anthropic", "gemini", "deepseek", "deterministic",
    }
    cfg_ok = (
        evidence.configuration.default_provider in valid_providers
        and evidence.configuration.cost_efficient_model != evidence.configuration.premium_model
        and evidence.configuration.routing_tier_count >= 2
        and len(evidence.configuration.available_providers) >= 2
    )
    check(
        ActivationCondition.CONFIGURATION_VALID,
        cfg_ok,
        f"invalid AI configuration (default={evidence.configuration.default_provider!r})",
    )

    state = (
        ActivationState.AI_PRODUCTION_READY
        if not failed
        else ActivationState.AI_PRODUCTION_BLOCKED
    )

    # Recommended models: cheapest-and-best at COST_EFFICIENT, best at PREMIUM.
    # Operator-only — never serialized to clients.
    if state is ActivationState.AI_PRODUCTION_READY and accepted_evals:
        scored = sorted(accepted_evals, key=lambda e: e.quality_score, reverse=True)
        recommended = (
            evidence.configuration.cost_efficient_model,
            evidence.configuration.premium_model,
            scored[0].model_identity,
        )
    else:
        recommended = ()

    return ActivationVerdict(
        state=state,
        passed=tuple(passed),
        failed=tuple(failed),
        reasons=tuple(reasons),
        recommended_models=tuple(dict.fromkeys(recommended)),  # dedupe, preserve order
    )


def build_evidence_from_benchmark(
    *,
    benchmark: BenchmarkEvidence,
    successful_evaluations: tuple[ModelEvaluationEvidence, ...],
    configuration: ConfigurationEvidence,
    tools: ToolEvidence,
    privacy: PrivacyEvidence,
    fail_closed: FailClosedEvidence,
    required_quality_threshold: float = 60.0,
    structured_output_required: bool = True,
) -> ActivationEvidence:
    """Convenience builder for the typical evidence shape."""
    return ActivationEvidence(
        benchmark=benchmark,
        successful_evaluations=successful_evaluations,
        configuration=configuration,
        tools=tools,
        privacy=privacy,
        fail_closed=fail_closed,
        required_quality_threshold=required_quality_threshold,
        structured_output_required=structured_output_required,
    )


__all__ = [
    "ActivationCondition",
    "ActivationState",
    "ActivationVerdict",
    "build_evidence_from_benchmark",
    "evaluate_activation",
]
