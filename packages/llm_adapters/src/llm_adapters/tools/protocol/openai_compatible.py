"""OpenAI / DeepSeek compatible function-calling protocol adapter.

OpenAI Chat Completions and DeepSeek Chat Completions share the same
``tools`` / ``tool_calls`` / ``role=tool`` wire format. This module is
the single implementation; both provider adapters import it. DSP tool
names and engines are not referenced except via the public manifest.
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


def declarations_as_openai_tools(
    manifest: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build OpenAI/DeepSeek ``tools`` from ``public_manifest()`` only."""
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
                "type": "function",
                "function": {
                    "name": to_provider_name(decl.name),
                    "description": decl.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
        )
    return tools


def _coerce_arguments(raw: Any) -> tuple[Mapping[str, Any] | None, str | None]:
    if raw is None:
        return {}, None
    if isinstance(raw, Mapping):
        return dict(raw), None
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return {}, None
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None, "tool call arguments are not valid JSON"
        if not isinstance(parsed, Mapping):
            return None, "tool call arguments must be a JSON object"
        return dict(parsed), None
    return None, "tool call arguments must be an object or JSON string"


def _extract_tool_call_dicts(payload: Any) -> tuple[list[Any] | None, str | None]:
    """Normalize several OpenAI-compatible payload shapes into a list."""
    if payload is None:
        return None, "missing tool-call payload"
    if isinstance(payload, list):
        return list(payload), None
    if not isinstance(payload, Mapping):
        return None, "tool-call payload must be an object or list"
    if "tool_calls" in payload:
        calls = payload.get("tool_calls")
        if not isinstance(calls, list):
            return None, "tool_calls must be a list"
        return list(calls), None
    message = payload.get("message")
    if isinstance(message, Mapping) and "tool_calls" in message:
        calls = message.get("tool_calls")
        if not isinstance(calls, list):
            return None, "message.tool_calls must be a list"
        return list(calls), None
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            inner = (
                first.get("message")
                if isinstance(first.get("message"), Mapping)
                else first
            )
            if isinstance(inner, Mapping) and "tool_calls" in inner:
                calls = inner.get("tool_calls")
                if not isinstance(calls, list):
                    return None, "choices[0].message.tool_calls must be a list"
                return list(calls), None
    if payload.get("type") == "function" or "function" in payload:
        return [payload], None
    return None, "no tool_calls found in payload"


def openai_payload_contains_tool_calls(payload: Any) -> bool:
    """True when an OpenAI-compatible payload actually requested tools."""
    extracted, _ = _extract_tool_call_dicts(payload)
    return bool(extracted)


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


def parse_openai_tool_calls(
    payload: Any,
    *,
    allowed_internal: Sequence[str] | frozenset[str],
) -> list[ToolCall | ToolCallOutcome]:
    """Normalize OpenAI/DeepSeek tool_calls into internal ToolCall values."""
    allowed = frozenset(allowed_internal)
    extracted, extract_error = _extract_tool_call_dicts(payload)
    if extracted is None:
        return [
            _malformed(
                "malformed", "unknown", extract_error or "malformed tool-call payload"
            )
        ]
    parsed: list[ToolCall | ToolCallOutcome] = []
    for index, item in enumerate(extracted):
        if not isinstance(item, Mapping):
            parsed.append(
                _malformed(
                    f"malformed-{index}", "unknown", "tool call is not an object"
                )
            )
            continue
        call_id = item.get("id")
        if not isinstance(call_id, str) or not call_id:
            parsed.append(
                _malformed(f"malformed-{index}", "unknown", "tool call missing id")
            )
            continue
        function = item.get("function")
        if not isinstance(function, Mapping):
            parsed.append(
                _malformed(call_id, "unknown", "tool call missing function object")
            )
            continue
        provider_name = function.get("name")
        if not isinstance(provider_name, str) or not provider_name:
            parsed.append(
                _malformed(call_id, "unknown", "tool call missing function name")
            )
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
        arguments, arg_error = _coerce_arguments(function.get("arguments"))
        if arguments is None:
            parsed.append(
                _malformed(call_id, internal, arg_error or "malformed arguments")
            )
            continue
        parsed.append(ToolCall(call_id=call_id, name=internal, arguments=arguments))
    return parsed


def format_openai_tool_messages(
    outcomes: Sequence[ToolCallOutcome],
) -> list[dict[str, Any]]:
    """Map outcomes to OpenAI/DeepSeek ``role=tool`` messages."""
    messages: list[dict[str, Any]] = []
    for outcome in outcomes:
        payload = safe_provider_payload(outcome)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": outcome.call_id,
                "content": json.dumps(payload, separators=(",", ":"), sort_keys=True),
            }
        )
    return messages


class OpenAICompatibleToolCalling:
    """Mixin used by both OpenAIAdapter and DeepSeekAdapter.

    Keeps provider-specific function-calling format inside the provider
    adapters without duplicating protocol logic.
    """

    def tool_declarations(
        self, manifest: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        return declarations_as_openai_tools(manifest)

    def payload_contains_tool_calls(self, payload: Any) -> bool:
        return openai_payload_contains_tool_calls(payload)

    def parse_tool_calls(
        self,
        payload: Any,
        *,
        allowed_internal: Sequence[str] | frozenset[str],
    ) -> list[ToolCall | ToolCallOutcome]:
        return parse_openai_tool_calls(payload, allowed_internal=allowed_internal)

    def format_tool_results(
        self, outcomes: Sequence[ToolCallOutcome]
    ) -> list[dict[str, Any]]:
        return format_openai_tool_messages(outcomes)

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
    "OpenAICompatibleToolCalling",
    "declarations_as_openai_tools",
    "format_openai_tool_messages",
    "openai_payload_contains_tool_calls",
    "parse_openai_tool_calls",
]
