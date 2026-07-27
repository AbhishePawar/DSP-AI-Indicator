"""External LLM provider adapters — outside frozen copilot domain."""

from llm_adapters.config import LLMPlatformConfig, load_llm_config
from llm_adapters.registry import ProviderRegistry, build_default_registry
from llm_adapters.service import CopilotCompleteService, CopilotCompleteResult

__version__ = "0.1.0"

__all__ = [
    "CopilotCompleteResult",
    "CopilotCompleteService",
    "LLMPlatformConfig",
    "ProviderRegistry",
    "__version__",
    "build_default_registry",
    "load_llm_config",
]
