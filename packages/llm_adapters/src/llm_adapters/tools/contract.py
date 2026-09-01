"""Provider-neutral DSP tool contract.

A DSP tool is a typed, deterministic server-side capability exposed to
the LLM. Tools are **not** free-form Python. They have:

- a stable name (e.g. ``dsp.valuation``)
- a version (semver-ish string)
- a description (PUBLIC — no methodology leak)
- a typed input schema
- a typed output schema
- a deterministic implementation
- a provenance / source-of-truth reference
- a validation status

The contract is independent of any LLM provider. The LLM receives only
a manifest of public names + descriptions, then requests tools by name.
The dispatcher never returns raw provider responses, raw model output,
or chain-of-thought.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, runtime_checkable


class ToolStatus(str, Enum):
    """Status of one tool invocation."""

    OK = "ok"
    UNAVAILABLE = "unavailable"  # data missing or upstream unreachable
    FAILED = "failed"  # calculation failed
    INVALID_INPUT = "invalid_input"  # caller violated schema
    UNAUTHORIZED = "unauthorized"  # backend refused the call


@dataclass(frozen=True, slots=True)
class ToolInputField:
    """One field of a tool's typed input schema."""

    name: str
    type: str  # e.g. "string", "integer", "number", "object"
    required: bool = True
    description: str = ""


@dataclass(frozen=True, slots=True)
class ToolOutputField:
    """One field of a tool's typed output schema."""

    name: str
    type: str
    required: bool = True
    description: str = ""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Provider-neutral tool specification.

    ``description`` is PUBLIC and may be sent to the LLM. ``provenance``
    is the canonical DSP source-of-truth reference; it is operator-side
    telemetry, not a model input.
    """

    name: str
    version: str
    description: str
    provenance: str
    input_schema: tuple[ToolInputField, ...]
    output_schema: tuple[ToolOutputField, ...]
    validation_status: str = "validated"
    deterministic: bool = True


@dataclass(frozen=True, slots=True)
class ToolResult:
    """Provider-neutral typed tool result.

    Carries ONLY what the LLM needs to reason over. Never carries
    API keys, internal prompts, chain-of-thought, provider model
    identifiers, costs, or raw provider responses.
    """

    tool_name: str
    tool_version: str
    status: ToolStatus
    result: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    calculation_metadata: Mapping[str, Any]
    limitations: tuple[str, ...]

    def is_success(self) -> bool:
        return self.status is ToolStatus.OK


# --- private fields that may never appear inside a ToolResult --------------


_PRIVATE_FIELDS: frozenset[str] = frozenset(
    {
        "provider", "model", "routing_tier", "routing_reasons",
        "confidence_requirement", "estimated_cost_usd", "input_tokens",
        "output_tokens", "latency_ms", "model_score", "routing_criteria",
        "internal_prompt", "tool_calls", "tool_results", "raw_ai_response",
        "internal_validation", "chain_of_thought", "api_key",
    }
)


def assert_no_tool_leakage(payload: Mapping[str, Any]) -> None:
    """Defence-in-depth guard: tool results may not carry private fields."""
    leaked = sorted(set(payload.keys()) & _PRIVATE_FIELDS)
    if leaked:
        raise ValueError(f"private fields leaked into tool result: {leaked}")


# --- backend protocol -----------------------------------------------------


@runtime_checkable
class DSPToolBackend(Protocol):
    """The narrow subset of DSP platform methods a tool may call.

    Tools are NEVER given direct Python objects. They receive a backend
    that exposes ONLY canonical DSP methods. The default implementation
    will be the ``DSPPlatform`` façade; tests inject a stub.
    """

    # financial
    def get_authenticated_financial_statements(
        self, symbol: str, *, exchange: str | None = None, **kwargs: Any
    ) -> Any: ...
    def financial_statement_health(self) -> Mapping[str, Any]: ...
    # analysis
    def analyze_company(self, request: Any) -> Any: ...
    def compare_companies(self, packs: Any) -> Any: ...
    # committee / copilot (deterministic explainers)
    def ask_research_copilot(self, question: str, **kwargs: Any) -> Any: ...
    # research
    def build_research_object(self, symbol: str, **kwargs: Any) -> Any: ...
    def get_research_snapshot(self, snapshot_id: str) -> Any: ...
    # copilot 2.0 (orchestration only — not an LLM call)
    def run_copilot_v2(self, **kwargs: Any) -> Any: ...


__all__ = [
    "DSPToolBackend",
    "ToolInputField",
    "ToolOutputField",
    "ToolResult",
    "ToolSpec",
    "ToolStatus",
    "assert_no_tool_leakage",
]
