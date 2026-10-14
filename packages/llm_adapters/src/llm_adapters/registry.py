"""Backend provider registry with runtime credential support."""

from __future__ import annotations

from typing import Any

from llm_adapters.anthropic_adapter import AnthropicAdapter
from llm_adapters.config import LLMPlatformConfig, ProviderName, load_llm_config
from llm_adapters.deepseek_adapter import DeepSeekAdapter
from llm_adapters.gemini_adapter import GeminiDirectAdapter
from llm_adapters.generic_openai_adapter import GenericOpenAIAdapter
from llm_adapters.interfaces import ProviderAdapter
from llm_adapters.openai_adapter import OpenAIDirectAdapter
from llm_adapters.runtime_store import get_runtime_store

_OPENAI_COMPATIBLE_BASES = {
    "openrouter": ("https://openrouter.ai/api/v1", {"HTTP-Referer": "https://dspaiindicator.com"}),
    "groq": ("https://api.groq.com/openai/v1", {}),
    "mistral": ("https://api.mistral.ai/v1", {}),
    "xai": ("https://api.x.ai/v1", {}),
    "together": ("https://api.together.xyz/v1", {}),
    "fireworks": ("https://api.fireworks.ai/inference/v1", {}),
    "perplexity": ("https://api.perplexity.ai", {}),
    "cohere": ("https://api.cohere.com/v2", {}),
    "ollama": ("http://localhost:11434/v1", {}),
}


class ProviderRegistry:
    """Registry of external LLM provider adapters."""

    def __init__(self, config: LLMPlatformConfig | None = None) -> None:
        self._config = config or load_llm_config()
        self._direct_adapters: dict[str, ProviderAdapter] = {}
        self._adapters: dict[str, ProviderAdapter] = {}
        self._extended_adapters: dict[str, ProviderAdapter] = {}
        self._rebuild_adapters()

    def _rebuild_adapters(self) -> None:
        store = get_runtime_store()

        # Build direct core adapters with runtime secret overlay
        gemini_cfg = self._config
        gemini_secret = store.get_credential("gemini")
        gemini_model = store.get_provider_config("gemini")
        if gemini_secret or (gemini_model and gemini_model.selected_model):
            gemini_cfg = LLMPlatformConfig(
                default_provider=self._config.default_provider,
                openai_api_key=self._config.openai_api_key,
                anthropic_api_key=self._config.anthropic_api_key,
                gemini_api_key=gemini_secret or self._config.gemini_api_key,
                deepseek_api_key=self._config.deepseek_api_key,
                openai_model=self._config.openai_model,
                anthropic_model=self._config.anthropic_model,
                gemini_model=(gemini_model.selected_model if gemini_model and gemini_model.selected_model else self._config.gemini_model),
                deepseek_model=self._config.deepseek_model,
                request_timeout_seconds=self._config.request_timeout_seconds,
                max_retries=self._config.max_retries,
                provider_mode=self._config.provider_mode,
            )

        openai_cfg = self._config
        openai_secret = store.get_credential("openai")
        openai_model = store.get_provider_config("openai")
        if openai_secret or (openai_model and openai_model.selected_model):
            openai_cfg = LLMPlatformConfig(
                default_provider=self._config.default_provider,
                openai_api_key=openai_secret or self._config.openai_api_key,
                anthropic_api_key=self._config.anthropic_api_key,
                gemini_api_key=self._config.gemini_api_key,
                deepseek_api_key=self._config.deepseek_api_key,
                openai_model=(openai_model.selected_model if openai_model and openai_model.selected_model else self._config.openai_model),
                anthropic_model=self._config.anthropic_model,
                gemini_model=self._config.gemini_model,
                deepseek_model=self._config.deepseek_model,
                request_timeout_seconds=self._config.request_timeout_seconds,
                max_retries=self._config.max_retries,
                provider_mode=self._config.provider_mode,
            )

        anthropic_cfg = self._config
        anthropic_secret = store.get_credential("anthropic")
        anthropic_model = store.get_provider_config("anthropic")
        if anthropic_secret or (anthropic_model and anthropic_model.selected_model):
            anthropic_cfg = LLMPlatformConfig(
                default_provider=self._config.default_provider,
                openai_api_key=self._config.openai_api_key,
                anthropic_api_key=anthropic_secret or self._config.anthropic_api_key,
                gemini_api_key=self._config.gemini_api_key,
                deepseek_api_key=self._config.deepseek_api_key,
                openai_model=self._config.openai_model,
                anthropic_model=(anthropic_model.selected_model if anthropic_model and anthropic_model.selected_model else self._config.anthropic_model),
                gemini_model=self._config.gemini_model,
                deepseek_model=self._config.deepseek_model,
                request_timeout_seconds=self._config.request_timeout_seconds,
                max_retries=self._config.max_retries,
                provider_mode=self._config.provider_mode,
            )

        deepseek_cfg = self._config
        deepseek_secret = store.get_credential("deepseek")
        deepseek_model = store.get_provider_config("deepseek")
        if deepseek_secret or (deepseek_model and deepseek_model.selected_model):
            deepseek_cfg = LLMPlatformConfig(
                default_provider=self._config.default_provider,
                openai_api_key=self._config.openai_api_key,
                anthropic_api_key=self._config.anthropic_api_key,
                gemini_api_key=self._config.gemini_api_key,
                deepseek_api_key=deepseek_secret or self._config.deepseek_api_key,
                openai_model=self._config.openai_model,
                anthropic_model=self._config.anthropic_model,
                gemini_model=self._config.gemini_model,
                deepseek_model=(deepseek_model.selected_model if deepseek_model and deepseek_model.selected_model else self._config.deepseek_model),
                request_timeout_seconds=self._config.request_timeout_seconds,
                max_retries=self._config.max_retries,
                provider_mode=self._config.provider_mode,
            )

        self._direct_adapters = {
            "openai": OpenAIDirectAdapter(openai_cfg),
            "gemini": GeminiDirectAdapter(gemini_cfg),
            "anthropic": AnthropicAdapter(anthropic_cfg),
            "deepseek": DeepSeekAdapter(deepseek_cfg),
        }

        # Core providers always call their official direct APIs.
        self._adapters = dict(self._direct_adapters)

        # Dynamically register OpenAI-compatible extended providers
        for pid, (base_url, extra_hdrs) in _OPENAI_COMPATIBLE_BASES.items():
            prov_rec = store.get_provider_config(pid)
            sec = store.get_credential(pid)
            model_label = prov_rec.selected_model if prov_rec else ""
            eff_base_url = (prov_rec.base_url if prov_rec and prov_rec.base_url else base_url)
            self._extended_adapters[pid] = GenericOpenAIAdapter(
                pid,
                base_url=eff_base_url,
                api_key=sec,
                model_label=model_label,
                timeout_seconds=prov_rec.timeout_seconds if prov_rec else 30.0,
                extra_headers=extra_hdrs,
            )

    @property
    def config(self) -> LLMPlatformConfig:
        return self._config

    def refresh(self) -> None:
        """Re-sync adapters with the latest runtime store configuration."""
        self._rebuild_adapters()

    def get(self, provider_id: str) -> ProviderAdapter | None:
        pid = provider_id.lower()
        if pid in self._adapters:
            return self._adapters[pid]
        if pid in self._extended_adapters:
            return self._extended_adapters[pid]
        self._rebuild_adapters()
        if pid in self._adapters:
            return self._adapters[pid]
        return self._extended_adapters.get(pid)

    def direct_fallback(self, provider_id: str) -> ProviderAdapter | None:
        """Return no secondary adapter: registered core providers are already direct."""
        del provider_id
        return None

    def list_providers(self, include_all: bool = False) -> list[dict[str, object]]:
        if not include_all:
            return [
                {
                    "id": adapter.provider_id,
                    "model": adapter.model_label,
                    "configured": adapter.is_configured(),
                    "capabilities": ["chat", "compare", "streaming"],
                }
                for adapter in self._adapters.values()
            ]

        store = get_runtime_store()
        res = []
        for p in store.list_providers(category="ai"):
            adapter = self.get(p.provider_id)
            configured = adapter.is_configured() if adapter else p.has_credential
            res.append({
                "id": p.provider_id,
                "name": p.display_name,
                "model": p.selected_model,
                "configured": configured,
                "is_active": p.is_active,
                "health_status": p.health_status.value,
                "capabilities": p.supported_capabilities,
            })
        return res

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
