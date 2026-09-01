"""Provider-neutral tool-calling representations.

These types are the internal language of the tool-call boundary. Provider
wire formats (OpenAI, DeepSeek, Gemini, Anthropic) must be normalized
into these types before DSP is involved, and must be normalized back
out after a ``ToolResult`` is produced.

DSP methodology never appears here. Provenance, engine names, and
provider credentials never appear here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from llm_adapters.tools.contract import ToolResult, ToolStatus


class ToolCallStatus(str, Enum):
    """Outcome of one provider-originated tool call.

    Distinct from ``ToolStatus`` so protocol-layer failures (malformed
    payload, unknown name, unauthorized) are first-class and fail-closed
    without pretending they were a DSP engine result.
    """

    OK = "ok"
    MALFORMED = "malformed"
    UNKNOWN_TOOL = "unknown_tool"
    UNAUTHORIZED = "unauthorized"
    INVALID_ARGUMENTS = "invalid_arguments"
    TOOL_FAILED = "tool_failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class ToolDeclaration:
    """Public tool declaration derived ONLY from ``public_manifest()``.

    Field descriptions and provenance are intentionally absent: the
    LLM is allowed to know name, version, description, and schemas.
    """

    name: str
    version: str
    description: str
    input_schema: tuple[Mapping[str, Any], ...]
    output_schema: tuple[Mapping[str, Any], ...]

    @classmethod
    def from_manifest_entry(cls, entry: Mapping[str, Any]) -> "ToolDeclaration":
        name = entry.get("name")
        version = entry.get("version")
        description = entry.get("description")
        input_schema = entry.get("input_schema")
        output_schema = entry.get("output_schema")
        if not isinstance(name, str) or not name:
            raise ValueError("manifest entry missing name")
        if not isinstance(version, str) or not version:
            raise ValueError("manifest entry missing version")
        if not isinstance(description, str):
            raise ValueError("manifest entry missing description")
        if not isinstance(input_schema, Sequence) or isinstance(input_schema, (str, bytes)):
            raise ValueError("manifest entry missing input_schema")
        if not isinstance(output_schema, Sequence) or isinstance(output_schema, (str, bytes)):
            raise ValueError("manifest entry missing output_schema")
        # Refuse provenance / internals if a caller tries to smuggle them.
        if "provenance" in entry or "validation_status" in entry:
            raise ValueError("manifest entry must not include provenance")
        return cls(
            name=name,
            version=version,
            description=description,
            input_schema=tuple(dict(item) for item in input_schema),
            output_schema=tuple(dict(item) for item in output_schema),
        )


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Provider-neutral request to invoke one approved DSP tool."""

    call_id: str
    name: str  # internal name, e.g. dsp.valuation
    arguments: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCallError:
    """Sanitized protocol/tool error. Never carries stack traces or secrets."""

    kind: ToolCallStatus
    message: str


@dataclass(frozen=True, slots=True)
class ToolCallOutcome:
    """Normalized result of one tool call, ready for provider export.

    ``result`` is the DSP ``ToolResult`` when the registry ran. Protocol
    rejections (malformed / unknown / unauthorized) leave it ``None``.
    ``audit`` is operator-side only and must never be serialized to the
    browser or mixed into provider wire formats by callers.
    """

    call_id: str
    tool_name: str
    status: ToolCallStatus
    result: ToolResult | None
    error: ToolCallError | None
    audit: Mapping[str, Any]

    def is_success(self) -> bool:
        return self.status is ToolCallStatus.OK

    def provider_payload(self) -> dict[str, Any]:
        """Sanitized envelope the protocol adapters may send back to an AI.

        Contains research-facing tool output only. No audit, no cost,
        no tokens, no provider identity, no prompts, no raw messages.
        Non-OK paths use the sanitized protocol error — never raw
        exception text from the registry.
        """
        if self.result is not None and self.status is ToolCallStatus.OK:
            return {
                "tool_name": self.result.tool_name,
                "tool_version": self.result.tool_version,
                "status": self.result.status.value,
                "result": dict(self.result.result),
                "evidence_refs": list(self.result.evidence_refs),
                "limitations": list(self.result.limitations),
            }
        message = self.error.message if self.error is not None else "tool call failed"
        tool_version = self.result.tool_version if self.result is not None else "0.0.0"
        return {
            "tool_name": self.tool_name,
            "tool_version": tool_version,
            "status": self.status.value,
            "result": {"reason": message},
            "evidence_refs": [],
            "limitations": [message],
        }


def tool_status_to_call_status(status: ToolStatus) -> ToolCallStatus:
    if status is ToolStatus.OK:
        return ToolCallStatus.OK
    if status is ToolStatus.INVALID_INPUT:
        return ToolCallStatus.INVALID_ARGUMENTS
    if status is ToolStatus.FAILED:
        return ToolCallStatus.TOOL_FAILED
    if status is ToolStatus.UNAVAILABLE:
        return ToolCallStatus.UNAVAILABLE
    if status is ToolStatus.UNAUTHORIZED:
        return ToolCallStatus.UNAUTHORIZED
    return ToolCallStatus.TOOL_FAILED


__all__ = [
    "ToolCall",
    "ToolCallError",
    "ToolCallOutcome",
    "ToolCallStatus",
    "ToolDeclaration",
    "tool_status_to_call_status",
]
