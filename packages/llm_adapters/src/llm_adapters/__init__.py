"""External LLM provider adapters — outside frozen copilot domain."""

from llm_adapters.config import LLMPlatformConfig, load_llm_config
from llm_adapters.registry import ProviderRegistry, build_default_registry
from llm_adapters.service import CopilotCompleteService, CopilotCompleteResult

__all__ = [
    "CopilotCompleteResult",
    "CopilotCompleteService",
    "LLMPlatformConfig",
    "build_default_registry",
    "load_llm_config",
    "ProviderRegistry",
]
