"""Backend provider registry."""

from __future__ import annotations

from llm_adapters.anthropic_adapter import AnthropicAdapter
from llm_adapters.config import LLMPlatformConfig, ProviderName, load_llm_config
from llm_adapters.gemini_adapter import GeminiAdapter
from llm_adapters.interfaces import ProviderAdapter
from llm_adapters.openai_adapter import OpenAIAdapter


class ProviderRegistry:
    """Registry of external LLM provider adapters."""

    def __init__(self, config: LLMPlatformConfig | None = None) -> None:
        self._config = config or load_llm_config()
        self._adapters: dict[str, ProviderAdapter] = {
            "openai": OpenAIAdapter(self._config),
            "anthropic": AnthropicAdapter(self._config),
            "gemini": GeminiAdapter(self._config),
        }

    @property
    def config(self) -> LLMPlatformConfig:
        return self._config

    def get(self, provider_id: str) -> ProviderAdapter | None:
        return self._adapters.get(provider_id)

    def list_providers(self) -> list[dict[str, object]]:
        return [
            {
                "id": adapter.provider_id,
                "model": adapter.model_label,
                "configured": adapter.is_configured(),
                "capabilities": ["chat", "compare", "streaming"],
            }
            for adapter in self._adapters.values()
        ]

    def resolve_active(self) -> tuple[ProviderName, ProviderAdapter | None]:
        provider_id = self._config.default_provider
        if provider_id == "deterministic":
            return provider_id, None
        adapter = self.get(provider_id)
        if adapter is None or not adapter.is_configured():
            return "deterministic", None
        return provider_id, adapter


def build_default_registry() -> ProviderRegistry:
    return ProviderRegistry(load_llm_config())
