"""Fail-closed DSP trusted-tool execution loop.

Provider-neutral contract:

AIProvider → ToolCall → ToolCallBoundary → ToolRegistry →
DSPPlatformToolAdapter → ToolResult → AIProvider → next ToolCall
or structured AIResearchOutput.

The loop never fabricates a final answer when a limit is hit, a tool
call is invalid, or a DSP tool fails. Chain-of-thought is not stored.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from llm_adapters.evaluation import ErrorCategory
from llm_adapters.orchestrator.evidence import evidence_catalog
from llm_adapters.orchestrator.provider import AICompletion, AIProvider
from llm_adapters.orchestrator.research_prompt import build_research_prompt
from llm_adapters.orchestrator.specification import ResearchSpecification
from llm_adapters.tools.protocol.dispatcher import (
    ToolCallBoundary,
    safe_provider_payload,
)
from llm_adapters.tools.protocol.models import ToolCall, ToolCallOutcome, ToolCallStatus

_INVALID_CALL_STATUSES = frozenset(
    {
        ToolCallStatus.MALFORMED,
        ToolCallStatus.UNKNOWN_TOOL,
        ToolCallStatus.UNAUTHORIZED,
        ToolCallStatus.INVALID_ARGUMENTS,
    }
)


@dataclass(frozen=True, slots=True)
class ToolLoopLimits:
    """Deterministic safety caps for one research request."""

    max_iterations: int = 6
    max_tool_calls: int = 12
    max_identical: int = 1
    max_provider_round_trips: int = 8

    def __post_init__(self) -> None:
        for name in (
            "max_iterations",
            "max_tool_calls",
            "max_identical",
            "max_provider_round_trips",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


DEFAULT_TOOL_LOOP_LIMITS = ToolLoopLimits()


@dataclass(frozen=True, slots=True)
class ToolLoopRun:
    """Internal loop outcome. Not a public/client type."""

    completion: AICompletion
    outcomes: tuple[ToolCallOutcome, ...]
    catalog: tuple[dict[str, Any], ...]
    prompt: tuple[str, ...]
    error_category: ErrorCategory
    stop_reason: str
    provider_round_trips: int
    tool_iterations: int
    ai_tool_calls: int


def call_fingerprint(call: ToolCall) -> str:
    """Canonical identity of one tool request: name + arguments."""
    payload = json.dumps(
        dict(call.arguments),
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"{call.name}:{payload}"


def fatal_tool_category(
    outcomes: Sequence[ToolCallOutcome],
) -> ErrorCategory | None:
    """Map a just-executed batch to a fail-closed category, if any."""
    for outcome in outcomes:
        if outcome.status in _INVALID_CALL_STATUSES:
            return ErrorCategory.INVALID_TOOL_CALL
        if outcome.status is ToolCallStatus.UNAVAILABLE:
            return ErrorCategory.TOOL_UNAVAILABLE
        if outcome.status is ToolCallStatus.TOOL_FAILED:
            return ErrorCategory.TOOL_FAILURE
    return None


def _empty_completion() -> AICompletion:
    return AICompletion(
        status="failed",
        text=None,
        requested_calls=(),
        provider_id="unknown",
        model_label="unknown",
    )


def run_trusted_tool_loop(
    *,
    provider: AIProvider,
    spec: ResearchSpecification,
    boundary: ToolCallBoundary,
    initial_outcomes: tuple[ToolCallOutcome, ...],
    limits: ToolLoopLimits | None = None,
) -> ToolLoopRun:
    """Run sequential (and batched) DSP tool calls until a final answer.

    Fail closed on loop limits, invalid calls, DSP unavailability, and
    provider failure. Never treats leftover model text as a successful
    structured result when tools are still outstanding.
    """
    caps = limits or DEFAULT_TOOL_LOOP_LIMITS
    outcomes = list(initial_outcomes)
    catalog = evidence_catalog(tuple(outcomes))
    manifest = boundary.public_manifest()
    prompt = build_research_prompt(
        spec,
        evidence_catalog=catalog,
        tool_manifest=manifest,
    )
    seen: dict[str, int] = {}
    ai_tool_calls = 0
    iterations = 0
    round_trips = 0
    completion = _empty_completion()
    prior_payloads: tuple[dict[str, Any], ...] = ()
    prior_outcomes: tuple[ToolCallOutcome, ...] = ()

    def snapshot(
        category: ErrorCategory,
        reason: str,
    ) -> ToolLoopRun:
        return ToolLoopRun(
            completion=completion,
            outcomes=tuple(outcomes),
            catalog=evidence_catalog(tuple(outcomes)),
            prompt=prompt,
            error_category=category,
            stop_reason=reason,
            provider_round_trips=round_trips,
            tool_iterations=iterations,
            ai_tool_calls=ai_tool_calls,
        )

    while True:
        if round_trips >= caps.max_provider_round_trips:
            return snapshot(
                ErrorCategory.LOOP_LIMIT_EXCEEDED,
                "maximum provider round trips exceeded",
            )
        try:
            completion = provider.complete(
                prompt_parts=prompt,
                evidence_catalog=catalog,
                prior_tool_results=prior_payloads,
                tool_manifest=tuple(manifest),
                prior_outcomes=prior_outcomes,
            )
        except Exception:  # noqa: BLE001 — fail-closed, no exception leak
            completion = AICompletion(
                status="failed",
                text=None,
                requested_calls=(),
                provider_id=getattr(provider, "provider_id", "unknown"),
                model_label=getattr(provider, "model_label", "unknown"),
            )
            return snapshot(ErrorCategory.PROVIDER_FAILED, "provider failed")
        round_trips += 1

        if completion.status == "unavailable":
            return snapshot(
                ErrorCategory.PROVIDER_UNAVAILABLE,
                "provider unavailable",
            )
        if completion.status != "complete":
            return snapshot(ErrorCategory.PROVIDER_FAILED, "provider failed")

        requested = completion.requested_calls
        if not requested:
            return snapshot(ErrorCategory.NONE, "final provider response")

        if iterations >= caps.max_iterations:
            return snapshot(
                ErrorCategory.LOOP_LIMIT_EXCEEDED,
                "maximum tool iterations exceeded",
            )

        pending = [item for item in requested if isinstance(item, ToolCall)]
        if ai_tool_calls + len(pending) > caps.max_tool_calls:
            return snapshot(
                ErrorCategory.LOOP_LIMIT_EXCEEDED,
                "maximum tool-call limit exceeded",
            )

        batch_fps: list[str] = []
        for call in pending:
            fingerprint = call_fingerprint(call)
            already = seen.get(fingerprint, 0) + batch_fps.count(fingerprint)
            if already >= caps.max_identical:
                return snapshot(
                    ErrorCategory.LOOP_LIMIT_EXCEEDED,
                    "repeated identical tool call",
                )
            batch_fps.append(fingerprint)

        executed = boundary.execute_many(requested)
        for fingerprint in batch_fps:
            seen[fingerprint] = seen.get(fingerprint, 0) + 1
        ai_tool_calls += len(pending)
        iterations += 1
        outcomes.extend(executed)

        fatal = fatal_tool_category(executed)
        catalog = evidence_catalog(tuple(outcomes))
        prompt = build_research_prompt(
            spec,
            evidence_catalog=catalog,
            tool_manifest=manifest,
        )
        prior_payloads = tuple(safe_provider_payload(item) for item in executed)
        prior_outcomes = executed
        if fatal is not None:
            return snapshot(fatal, "tool call rejected or failed")


__all__ = [
    "DEFAULT_TOOL_LOOP_LIMITS",
    "ToolLoopLimits",
    "ToolLoopRun",
    "call_fingerprint",
    "fatal_tool_category",
    "run_trusted_tool_loop",
]
