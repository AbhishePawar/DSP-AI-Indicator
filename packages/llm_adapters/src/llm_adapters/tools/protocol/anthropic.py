"""Anthropic tool-use protocol adapter.

Anthropic Messages API uses ``tools`` on the request, ``tool_use``
content blocks from the model, and ``tool_result`` content blocks on
the follow-up user message.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from llm_adapters.tools.protocol.dispatcher import (
    ToolCallBoundary,
    safe_provider_payload,
)
from llm_adapters.tools.protocol.models import (
    ToolCall,
    ToolCallError,
    ToolCallOutcome,
    ToolCallStatus,
    ToolDeclaration,
)
from llm_adapters.tools.protocol.names import (
    allowed_names_from_manifest,
    resolve_internal_name,
    to_provider_name,
)


def _json_type(type_str: str) -> str:
    mapping = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "object": "object",
        "array": "array",
    }
    return mapping.get(type_str, "string")


def declarations_as_anthropic_tools(
    manifest: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build Anthropic ``tools`` from ``public_manifest()`` only."""
    tools: list[dict[str, Any]] = []
    for entry in manifest:
        decl = ToolDeclaration.from_manifest_entry(entry)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for field in decl.input_schema:
            name = field.get("name")
            if not isinstance(name, str) or not name:
                continue
            properties[name] = {"type": _json_type(str(field.get("type", "string")))}
            if field.get("required", True):
                required.append(name)
        tools.append(
            {
                "name": to_provider_name(decl.name),
                "description": decl.description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return tools


def _malformed(call_id: str, tool_name: str, message: str) -> ToolCallOutcome:
    cid = call_id or "malformed"
    return ToolCallOutcome(
        call_id=cid,
        tool_name=tool_name or "unknown",
        status=ToolCallStatus.MALFORMED,
        result=None,
        error=ToolCallError(kind=ToolCallStatus.MALFORMED, message=message),
        audit={
            "call_id": cid,
            "tool_name": tool_name or "unknown",
            "status": "malformed",
        },
    )


def _extract_tool_use_blocks(payload: Any) -> tuple[list[Any] | None, str | None]:
    if payload is None:
        return None, "missing tool_use payload"
    if isinstance(payload, list):
        return list(payload), None
    if not isinstance(payload, Mapping):
        return None, "tool_use payload must be an object or list"
    if payload.get("type") == "tool_use":
        return [payload], None
    content = payload.get("content")
    if isinstance(content, list):
        return [block for block in content if isinstance(block, Mapping)], None
    return None, "no tool_use found in payload"


def anthropic_payload_contains_tool_use(payload: Any) -> bool:
    """True when an Anthropic payload contains at least one tool_use block."""
    extracted, _ = _extract_tool_use_blocks(payload)
    if not extracted:
        return False
    return any(
        isinstance(item, Mapping) and item.get("type") == "tool_use"
        for item in extracted
    )


def parse_anthropic_tool_use(
    payload: Any,
    *,
    allowed_internal: Sequence[str] | frozenset[str],
) -> list[ToolCall | ToolCallOutcome]:
    allowed = frozenset(allowed_internal)
    extracted, extract_error = _extract_tool_use_blocks(payload)
    if extracted is None:
        return [
            _malformed(
                "malformed", "unknown", extract_error or "malformed tool_use payload"
            )
        ]
    parsed: list[ToolCall | ToolCallOutcome] = []
    skipped_non_tool = 0
    for index, item in enumerate(extracted):
        if not isinstance(item, Mapping):
            parsed.append(
                _malformed(
                    f"malformed-{index}", "unknown", "content block is not an object"
                )
            )
            continue
        block_type = item.get("type")
        if block_type == "text":
            skipped_non_tool += 1
            continue
        if block_type is not None and block_type != "tool_use":
            parsed.append(
                _malformed(
                    (
                        item.get("id")
                        if isinstance(item.get("id"), str)
                        else f"malformed-{index}"
                    ),
                    "unknown",
                    "content block is not tool_use",
                )
            )
            continue
        if block_type is None and "name" not in item:
            skipped_non_tool += 1
            continue
        call_id = item.get("id")
        if not isinstance(call_id, str) or not call_id:
            parsed.append(
                _malformed(f"malformed-{index}", "unknown", "tool_use missing id")
            )
            continue
        provider_name = item.get("name")
        if not isinstance(provider_name, str) or not provider_name:
            parsed.append(_malformed(call_id, "unknown", "tool_use missing name"))
            continue
        internal = resolve_internal_name(provider_name, allowed_internal=allowed)
        if internal is None:
            parsed.append(
                ToolCallOutcome(
                    call_id=call_id,
                    tool_name=provider_name,
                    status=ToolCallStatus.UNKNOWN_TOOL,
                    result=None,
                    error=ToolCallError(
                        kind=ToolCallStatus.UNKNOWN_TOOL,
                        message="unknown or unapproved tool",
                    ),
                    audit={
                        "call_id": call_id,
                        "tool_name": provider_name,
                        "status": "unknown_tool",
                    },
                )
            )
            continue
        raw_input = item.get("input", {})
        if raw_input is None:
            raw_input = {}
        if isinstance(raw_input, str):
            try:
                raw_input = json.loads(raw_input)
            except json.JSONDecodeError:
                parsed.append(
                    _malformed(call_id, internal, "tool_use input is not valid JSON")
                )
                continue
        if not isinstance(raw_input, Mapping):
            parsed.append(
                _malformed(call_id, internal, "tool_use input must be an object")
            )
            continue
        parsed.append(
            ToolCall(call_id=call_id, name=internal, arguments=dict(raw_input))
        )
    if not parsed and skipped_non_tool:
        return [_malformed("malformed", "unknown", "no tool_use found in payload")]
    return parsed


def format_anthropic_tool_results(
    outcomes: Sequence[ToolCallOutcome],
) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for outcome in outcomes:
        payload = safe_provider_payload(outcome)
        is_error = outcome.status is not ToolCallStatus.OK
        blocks.append(
            {
                "type": "tool_result",
                "tool_use_id": outcome.call_id,
                "content": json.dumps(payload, separators=(",", ":"), sort_keys=True),
                "is_error": is_error,
            }
        )
    return blocks


class AnthropicToolCalling:
    """Mixin for AnthropicAdapter — Anthropic tool-use format stays here."""

    def tool_declarations(
        self, manifest: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        return declarations_as_anthropic_tools(manifest)

    def payload_contains_tool_calls(self, payload: Any) -> bool:
        return anthropic_payload_contains_tool_use(payload)

    def parse_tool_calls(
        self,
        payload: Any,
        *,
        allowed_internal: Sequence[str] | frozenset[str],
    ) -> list[ToolCall | ToolCallOutcome]:
        return parse_anthropic_tool_use(payload, allowed_internal=allowed_internal)

    def format_tool_results(
        self, outcomes: Sequence[ToolCallOutcome]
    ) -> list[dict[str, Any]]:
        return format_anthropic_tool_results(outcomes)

    def allowed_names_from_manifest(
        self, manifest: Sequence[Mapping[str, Any]]
    ) -> frozenset[str]:
        return allowed_names_from_manifest(manifest)

    def execute_provider_tool_calls(
        self,
        payload: Any,
        boundary: ToolCallBoundary,
    ) -> tuple[tuple[ToolCallOutcome, ...], list[dict[str, Any]]]:
        parsed = self.parse_tool_calls(
            payload, allowed_internal=boundary.allowed_names()
        )
        outcomes = boundary.execute_many(parsed)
        return outcomes, self.format_tool_results(outcomes)


__all__ = [
    "AnthropicToolCalling",
    "anthropic_payload_contains_tool_use",
    "declarations_as_anthropic_tools",
    "format_anthropic_tool_results",
    "parse_anthropic_tool_use",
]
