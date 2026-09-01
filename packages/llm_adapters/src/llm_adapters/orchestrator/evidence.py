"""Gather DSP evidence through ToolCallBoundary only."""

from __future__ import annotations

from typing import Any, Mapping

from llm_adapters.orchestrator.specification import ResearchSpecification
from llm_adapters.tools.protocol.dispatcher import ToolCallBoundary, safe_provider_payload
from llm_adapters.tools.protocol.models import ToolCall, ToolCallOutcome, ToolCallStatus


def gather_specified_tools(
    spec: ResearchSpecification,
    boundary: ToolCallBoundary,
) -> tuple[ToolCallOutcome, ...]:
    """Prefetch required tools. Never fabricates a result on failure."""
    calls: list[ToolCall] = []
    for index, name in enumerate(spec.required_tools):
        arguments: dict[str, Any] = {"symbol": spec.symbol}
        if spec.exchange:
            arguments["exchange"] = spec.exchange
        calls.append(
            ToolCall(
                call_id=f"prefetch-{index}-{name}",
                name=name,
                arguments=arguments,
            )
        )
    return boundary.execute_many(calls)


def evidence_catalog(
    outcomes: tuple[ToolCallOutcome, ...],
) -> tuple[dict[str, Any], ...]:
    """Public-to-AI catalog: sanitized payloads keyed by evidence id."""
    items: list[dict[str, Any]] = []
    for outcome in outcomes:
        payload = safe_provider_payload(outcome)
        items.append(
            {
                "id": outcome.call_id,
                "tool_name": outcome.tool_name,
                "status": outcome.status.value,
                "payload": payload,
            }
        )
    return tuple(items)


def outcomes_by_tool(
    outcomes: tuple[ToolCallOutcome, ...],
) -> dict[str, ToolCallOutcome]:
    """Last outcome per tool name (prefetch then AI-requested)."""
    mapping: dict[str, ToolCallOutcome] = {}
    for outcome in outcomes:
        mapping[outcome.tool_name] = outcome
    return mapping


def ok_payload(outcome: ToolCallOutcome | None) -> Mapping[str, Any] | None:
    if outcome is None or outcome.status is not ToolCallStatus.OK:
        return None
    if outcome.result is None:
        return None
    return outcome.result.result


__all__ = [
    "evidence_catalog",
    "gather_specified_tools",
    "ok_payload",
    "outcomes_by_tool",
]
