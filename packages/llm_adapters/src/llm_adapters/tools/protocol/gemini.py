"""Gemini functionDeclarations / functionCall protocol adapter.

Gemini uses ``functionDeclarations`` on the request and ``functionCall``
/ ``functionResponse`` parts on the content. DSP names are mapped to
underscore form because Gemini forbids dots in function names.
"""

from __future__ import annotations

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


def _gemini_type(type_str: str) -> str:
    mapping = {
        "string": "STRING",
        "integer": "INTEGER",
        "number": "NUMBER",
        "boolean": "BOOLEAN",
        "object": "OBJECT",
        "array": "ARRAY",
    }
    return mapping.get(type_str, "STRING")


def declarations_as_gemini_functions(
    manifest: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build Gemini ``functionDeclarations`` from ``public_manifest()`` only."""
    declarations: list[dict[str, Any]] = []
    for entry in manifest:
        decl = ToolDeclaration.from_manifest_entry(entry)
        properties: dict[str, Any] = {}
        required: list[str] = []
        for field in decl.input_schema:
            name = field.get("name")
            if not isinstance(name, str) or not name:
                continue
            properties[name] = {"type": _gemini_type(str(field.get("type", "string")))}
            if field.get("required", True):
                required.append(name)
        declarations.append(
            {
                "name": to_provider_name(decl.name),
                "description": decl.description,
                "parameters": {
                    "type": "OBJECT",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return declarations


def gemini_tools_payload(manifest: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {"functionDeclarations": declarations_as_gemini_functions(manifest)}


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


def _extract_function_calls(payload: Any) -> tuple[list[Any] | None, str | None]:
    if payload is None:
        return None, "missing functionCall payload"
    if isinstance(payload, list):
        return list(payload), None
    if not isinstance(payload, Mapping):
        return None, "functionCall payload must be an object or list"
    if "functionCall" in payload:
        return [payload.get("functionCall")], None
    if "name" in payload and ("args" in payload or "arguments" in payload):
        return [payload], None
    parts = payload.get("parts")
    if isinstance(parts, list):
        calls = [
            p.get("functionCall")
            for p in parts
            if isinstance(p, Mapping) and "functionCall" in p
        ]
        return calls, None
    content = payload.get("content")
    if isinstance(content, Mapping) and isinstance(content.get("parts"), list):
        calls = [
            p.get("functionCall")
            for p in content["parts"]
            if isinstance(p, Mapping) and "functionCall" in p
        ]
        return calls, None
    candidates = payload.get("candidates")
    if isinstance(candidates, list) and candidates:
        first = candidates[0]
        if isinstance(first, Mapping):
            inner = (
                first.get("content")
                if isinstance(first.get("content"), Mapping)
                else first
            )
            if isinstance(inner, Mapping) and isinstance(inner.get("parts"), list):
                calls = [
                    p.get("functionCall")
                    for p in inner["parts"]
                    if isinstance(p, Mapping) and "functionCall" in p
                ]
                return calls, None
    return None, "no functionCall found in payload"


def gemini_payload_contains_function_calls(payload: Any) -> bool:
    """True when a Gemini payload contains at least one functionCall."""
    extracted, _ = _extract_function_calls(payload)
    if not extracted:
        return False
    return any(isinstance(item, Mapping) for item in extracted)


def parse_gemini_function_calls(
    payload: Any,
    *,
    allowed_internal: Sequence[str] | frozenset[str],
) -> list[ToolCall | ToolCallOutcome]:
    allowed = frozenset(allowed_internal)
    extracted, extract_error = _extract_function_calls(payload)
    if extracted is None:
        return [
            _malformed(
                "malformed",
                "unknown",
                extract_error or "malformed functionCall payload",
            )
        ]
    parsed: list[ToolCall | ToolCallOutcome] = []
    for index, item in enumerate(extracted):
        if not isinstance(item, Mapping):
            parsed.append(
                _malformed(
                    f"gemini-{index}", "unknown", "functionCall is not an object"
                )
            )
            continue
        provider_name = item.get("name")
        if not isinstance(provider_name, str) or not provider_name:
            parsed.append(
                _malformed(f"gemini-{index}", "unknown", "functionCall missing name")
            )
            continue
        raw_id = item.get("id")
        call_id = (
            raw_id
            if isinstance(raw_id, str) and raw_id
            else f"gemini-{index}-{provider_name}"
        )
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
        args = item.get("args", item.get("arguments", {}))
        if args is None:
            args = {}
        if not isinstance(args, Mapping):
            parsed.append(
                _malformed(call_id, internal, "functionCall args must be an object")
            )
            continue
        parsed.append(ToolCall(call_id=call_id, name=internal, arguments=dict(args)))
    return parsed


def format_gemini_function_responses(
    outcomes: Sequence[ToolCallOutcome],
) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for outcome in outcomes:
        payload = safe_provider_payload(outcome)
        parts.append(
            {
                "functionResponse": {
                    "name": (
                        to_provider_name(outcome.tool_name)
                        if outcome.tool_name.startswith("dsp.")
                        else outcome.tool_name.replace(".", "_")
                    ),
                    "response": payload,
                }
            }
        )
    return parts


class GeminiToolCalling:
    """Mixin for GeminiAdapter — Gemini wire format stays in this adapter."""

    def tool_declarations(
        self, manifest: Sequence[Mapping[str, Any]]
    ) -> dict[str, Any]:
        return gemini_tools_payload(manifest)

    def payload_contains_tool_calls(self, payload: Any) -> bool:
        return gemini_payload_contains_function_calls(payload)

    def parse_tool_calls(
        self,
        payload: Any,
        *,
        allowed_internal: Sequence[str] | frozenset[str],
    ) -> list[ToolCall | ToolCallOutcome]:
        return parse_gemini_function_calls(payload, allowed_internal=allowed_internal)

    def format_tool_results(
        self, outcomes: Sequence[ToolCallOutcome]
    ) -> list[dict[str, Any]]:
        return format_gemini_function_responses(outcomes)

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
    "GeminiToolCalling",
    "declarations_as_gemini_functions",
    "format_gemini_function_responses",
    "gemini_payload_contains_function_calls",
    "gemini_tools_payload",
    "parse_gemini_function_calls",
]
