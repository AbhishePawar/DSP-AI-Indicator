"""DSP trusted tool surface — public entry point."""

from __future__ import annotations

from llm_adapters.tools.contract import (
    DSPToolBackend,
    ToolInputField,
    ToolOutputField,
    ToolResult,
    ToolSpec,
    ToolStatus,
    assert_no_tool_leakage,
)
from llm_adapters.tools.dsp_platform_adapter import (
    DSPPlatformToolAdapter,
    ToolHealthState,
    reset_pack_cache,
)
from llm_adapters.tools.health import (
    AUTHENTICATION_REQUIRED,
    UNAVAILABLE,
    WIRED,
    ToolHealthReport,
    check_tool_health,
    is_comparison_backed,
    is_composition_backed,
    is_flat_backed,
)
from llm_adapters.tools.registry import (
    DEFAULT_TOOL_NAMES,
    ToolRegistry,
)

__all__ = [
    "AUTHENTICATION_REQUIRED",
    "DEFAULT_TOOL_NAMES",
    "DSPPlatformToolAdapter",
    "DSPToolBackend",
    "ToolHealthReport",
    "ToolHealthState",
    "ToolInputField",
    "ToolOutputField",
    "ToolRegistry",
    "ToolResult",
    "ToolSpec",
    "ToolStatus",
    "UNAVAILABLE",
    "WIRED",
    "assert_no_tool_leakage",
    "check_tool_health",
    "is_comparison_backed",
    "is_composition_backed",
    "is_flat_backed",
    "reset_pack_cache",
]
