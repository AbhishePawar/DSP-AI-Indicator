"""LLM provider configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

ProviderName = Literal["deterministic", "openai", "anthropic", "gemini", "deepseek"]
ProviderMode = Literal["direct", "gateway", "deterministic"]

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"

_PROVENANCE = ("llm_adapters.config", "dsp.llm.config.v1")


@dataclass(frozen=True, slots=True)
class LLMPlatformConfig:
    """Resolved LLM platform configuration."""

    default_provider: ProviderName
    openai_api_key: str | None
    anthropic_api_key: str | None
    gemini_api_key: str | None
    deepseek_api_key: str | None
    openai_model: str
    anthropic_model: str
    gemini_model: str
    deepseek_model: str
    request_timeout_seconds: float
    max_retries: int
    ai_gateway_api_key: str | None = None
    ai_gateway_base_url: str = "https://ai-gateway.vercel.sh/v1"
    direct_provider_fallback: bool = True
    provider_mode: ProviderMode = "direct"

    @property
    def has_external_provider(self) -> bool:
        if self.default_provider == "deterministic":
            return False
        if self.default_provider == "openai":
            return bool(self.openai_api_key or (self.provider_mode == "gateway" and self.ai_gateway_api_key))
        if self.default_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.default_provider == "gemini":
            return bool(self.gemini_api_key or self.ai_gateway_api_key)
        if self.default_provider == "deepseek":
            return bool(self.deepseek_api_key)
        return False


def _read_env(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def load_llm_config() -> LLMPlatformConfig:
    """Load provider configuration from environment variables."""
    default_raw = (
        _read_env("DEFAULT_AI_PROVIDER", "DSP_AI_DEFAULT_PROVIDER") or "gemini"
    ).lower()
    allowed = {"deterministic", "openai", "anthropic", "gemini", "deepseek"}
    default_provider: ProviderName = (
        default_raw if default_raw in allowed else "deterministic"
    )

    mode_raw = (_read_env("AI_PROVIDER_MODE", "DSP_AI_PROVIDER_MODE") or "direct").lower()
    provider_mode: ProviderMode = (
        mode_raw if mode_raw in {"direct", "gateway", "deterministic"} else "direct"
    )

    return LLMPlatformConfig(
        default_provider=default_provider,
        openai_api_key=_read_env(
            "OPENAI_API_KEY_4", "OPENAI_API_KEY", "DSP_AI_OPENAI_API_KEY"
        ),
        anthropic_api_key=_read_env("ANTHROPIC_API_KEY", "DSP_AI_ANTHROPIC_API_KEY"),
        gemini_api_key=_read_env("GEMINI_API_KEY", "DSP_AI_GEMINI_API_KEY"),
        deepseek_api_key=_read_env("DEEPSEEK_API_KEY", "DSP_AI_DEEPSEEK_API_KEY"),
        openai_model=_read_env("OPENAI_MODEL", "DSP_AI_OPENAI_MODEL")
        or DEFAULT_OPENAI_MODEL,
        anthropic_model=_read_env("ANTHROPIC_MODEL", "DSP_AI_ANTHROPIC_MODEL")
        or "claude-3-5-sonnet-20241022",
        gemini_model=_read_env("GEMINI_MODEL", "DSP_AI_GEMINI_MODEL")
        or DEFAULT_GEMINI_MODEL,
        deepseek_model=_read_env("DEEPSEEK_MODEL", "DSP_AI_DEEPSEEK_MODEL")
        or "deepseek-chat",
        request_timeout_seconds=float(_read_env("DSP_AI_LLM_TIMEOUT_SECONDS") or "30"),
        max_retries=int(_read_env("DSP_AI_LLM_MAX_RETRIES") or "2"),
        ai_gateway_api_key=_read_env("AI_GATEWAY_API_KEY"),
        ai_gateway_base_url=(
            _read_env("AI_GATEWAY_BASE_URL") or "https://ai-gateway.vercel.sh/v1"
        ).rstrip("/"),
        direct_provider_fallback=(
            _read_env("DSP_AI_DIRECT_PROVIDER_FALLBACK") or "true"
        ).lower()
        in {"1", "true", "yes", "on"},
        provider_mode=provider_mode,
    )
