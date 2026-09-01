"""Provider-neutral tool-call protocol adapters.

Wire formats for OpenAI, DeepSeek, Gemini, and Anthropic stay inside
the corresponding adapter modules. DSP sees only ``ToolCall`` /
``ToolCallOutcome``.
"""

from __future__ import annotations

from llm_adapters.tools.protocol.anthropic import (
    AnthropicToolCalling,
    anthropic_payload_contains_tool_use,
    declarations_as_anthropic_tools,
    format_anthropic_tool_results,
    parse_anthropic_tool_use,
)
from llm_adapters.tools.protocol.dispatcher import (
    ToolCallBoundary,
    safe_provider_payload,
)
from llm_adapters.tools.protocol.gemini import (
    GeminiToolCalling,
    declarations_as_gemini_functions,
    format_gemini_function_responses,
    gemini_payload_contains_function_calls,
    gemini_tools_payload,
    parse_gemini_function_calls,
)
from llm_adapters.tools.protocol.models import (
    ToolCall,
    ToolCallError,
    ToolCallOutcome,
    ToolCallStatus,
    ToolDeclaration,
    tool_status_to_call_status,
)
from llm_adapters.tools.protocol.names import (
    allowed_names_from_manifest,
    provider_name_map,
    resolve_internal_name,
    to_provider_name,
)
from llm_adapters.tools.protocol.openai_compatible import (
    OpenAICompatibleToolCalling,
    declarations_as_openai_tools,
    format_openai_tool_messages,
    openai_payload_contains_tool_calls,
    parse_openai_tool_calls,
)
from llm_adapters.tools.protocol.privacy import (
    ProtocolPrivacyError,
    assert_browser_pack_private_free,
    assert_provider_envelope_private_free,
    failed_privacy_envelope,
)

__all__ = [
    "AnthropicToolCalling",
    "GeminiToolCalling",
    "OpenAICompatibleToolCalling",
    "ProtocolPrivacyError",
    "ToolCall",
    "ToolCallBoundary",
    "ToolCallError",
    "ToolCallOutcome",
    "ToolCallStatus",
    "ToolDeclaration",
    "allowed_names_from_manifest",
    "anthropic_payload_contains_tool_use",
    "assert_browser_pack_private_free",
    "assert_provider_envelope_private_free",
    "declarations_as_anthropic_tools",
    "declarations_as_gemini_functions",
    "declarations_as_openai_tools",
    "failed_privacy_envelope",
    "format_anthropic_tool_results",
    "format_gemini_function_responses",
    "format_openai_tool_messages",
    "gemini_payload_contains_function_calls",
    "gemini_tools_payload",
    "openai_payload_contains_tool_calls",
    "parse_anthropic_tool_use",
    "parse_gemini_function_calls",
    "parse_openai_tool_calls",
    "provider_name_map",
    "resolve_internal_name",
    "safe_provider_payload",
    "to_provider_name",
    "tool_status_to_call_status",
]
