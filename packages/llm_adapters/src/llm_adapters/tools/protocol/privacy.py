"""Privacy guards for the tool-call protocol layer.

Tool results that flow back to an AI provider must pass the existing
``assert_no_tool_leakage`` contract plus a nested scan for credentials,
prompts, routing, cost, tokens, raw provider messages, and
chain-of-thought. Fail closed: a leak becomes a FAILED envelope rather
than a redacted secret.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from llm_adapters.tools.contract import assert_no_tool_leakage
from llm_adapters.privacy_boundary import assert_no_private_leakage


# Keys that must never appear in a provider-facing tool envelope,
# including nested mappings. Extends the contract-level set.
_PROTOCOL_PRIVATE_KEYS: frozenset[str] = frozenset(
    {
        "api_key",
        "openai_api_key",
        "anthropic_api_key",
        "gemini_api_key",
        "deepseek_api_key",
        "authorization",
        "x-api-key",
        "credentials",
        "provider_credentials",
        "internal_prompt",
        "private_prompt",
        "private_prompts",
        "dsp_instructions",
        "internal_dsp_instructions",
        "routing_reasons",
        "routing_tier",
        "routing_criteria",
        "estimated_cost_usd",
        "cost",
        "input_tokens",
        "output_tokens",
        "token_counts",
        "tokens",
        "usage",
        "raw_ai_response",
        "raw_provider_messages",
        "raw_provider_message",
        "raw_provider_messages_json",
        "chain_of_thought",
        "provider",
        "model",
        "model_score",
        "latency_ms",
        "internal_validation",
        "audit",
    }
)

_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*\S+"),
)


class ProtocolPrivacyError(ValueError):
    """Raised when a provider-facing payload would leak private material."""


def _walk_keys(payload: Any, *, found: set[str]) -> None:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if isinstance(key, str):
                found.add(key)
            _walk_keys(value, found=found)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _walk_keys(item, found=found)


def _walk_strings(payload: Any, *, found: list[str]) -> None:
    if isinstance(payload, str):
        found.append(payload)
    elif isinstance(payload, Mapping):
        for value in payload.values():
            _walk_strings(value, found=found)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _walk_strings(item, found=found)


def assert_provider_envelope_private_free(payload: Mapping[str, Any]) -> None:
    """Fail closed if the envelope contains private keys or secret-shaped strings."""
    try:
        assert_no_tool_leakage(payload)
        nested: dict[str, Any] = dict(payload)
        result = nested.get("result")
        if isinstance(result, Mapping):
            assert_no_tool_leakage(result)
    except ValueError as exc:
        raise ProtocolPrivacyError(str(exc)) from exc
    keys: set[str] = set()
    _walk_keys(payload, found=keys)
    leaked = sorted(keys & _PROTOCOL_PRIVATE_KEYS)
    if leaked:
        raise ProtocolPrivacyError(f"private fields leaked into provider envelope: {leaked}")
    strings: list[str] = []
    _walk_strings(payload, found=strings)
    for text in strings:
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                raise ProtocolPrivacyError("secret-shaped value leaked into provider envelope")


def assert_browser_pack_private_free(pack: Mapping[str, Any]) -> None:
    """Browser-facing packs still go through the STEP 3B public-pack guard."""
    assert_no_private_leakage(dict(pack))


def failed_privacy_envelope(tool_name: str, tool_version: str = "0.0.0") -> dict[str, Any]:
    """Replacement envelope when a result fails privacy validation."""
    return {
        "tool_name": tool_name,
        "tool_version": tool_version,
        "status": "failed",
        "result": {"reason": "tool result failed privacy validation"},
        "evidence_refs": [],
        "limitations": ["privacy validation failed"],
    }


__all__ = [
    "ProtocolPrivacyError",
    "assert_browser_pack_private_free",
    "assert_provider_envelope_private_free",
    "failed_privacy_envelope",
]
