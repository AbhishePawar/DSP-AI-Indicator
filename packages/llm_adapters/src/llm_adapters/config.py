"""LLM provider configuration from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

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
    ai_gateway_base_url: str = ""
    direct_provider_fallback: bool = True
    provider_mode: ProviderMode = "direct"

    @property
    def has_configured_gateway(self) -> bool:
        """True only for an explicitly configured, non-Vercel gateway."""
        if self.provider_mode != "gateway" or not self.ai_gateway_api_key:
            return False
        try:
            parsed = urlsplit(self.ai_gateway_base_url.strip())
            host = (parsed.hostname or "").lower()
        except ValueError:
            return False
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or not host:
            return False
        blocked_hosts = ("vercel.sh", "vercel.com", "vercel.app")
        if any(host == suffix or host.endswith(f".{suffix}") for suffix in blocked_hosts):
            return False
        return True

    @property
    def has_external_provider(self) -> bool:
        if self.default_provider == "deterministic":
            return False
        if self.default_provider == "openai":
            return bool(self.openai_api_key or self.has_configured_gateway)
        if self.default_provider == "anthropic":
            return bool(self.anthropic_api_key)
        if self.default_provider == "gemini":
            return bool(self.gemini_api_key or self.has_configured_gateway)
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
    gateway_api_key = _read_env("AI_GATEWAY_API_KEY")
    gateway_base_url = _read_env("AI_GATEWAY_BASE_URL") or ""
    # Legacy hosted-gateway environment values must not silently route traffic.
    # A gateway is enabled only with an explicit valid URL and key; Vercel hosts
    # are rejected so the application cannot fall back to that external service.
    probe_config = LLMPlatformConfig(
        default_provider=default_provider,
        openai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        deepseek_api_key=None,
        openai_model=DEFAULT_OPENAI_MODEL,
        anthropic_model="claude-3-5-sonnet-20241022",
        gemini_model=DEFAULT_GEMINI_MODEL,
        deepseek_model="deepseek-chat",
        request_timeout_seconds=30.0,
        max_retries=2,
        ai_gateway_api_key=gateway_api_key,
        ai_gateway_base_url=gateway_base_url,
        provider_mode="gateway",
    )
    gateway_is_valid = probe_config.has_configured_gateway
    provider_mode: ProviderMode = (
        "deterministic"
        if mode_raw == "deterministic"
        else "gateway"
        if mode_raw == "gateway" and gateway_is_valid
        else "direct"
    )

    return LLMPlatformConfig(
        default_provider=default_provider,
        openai_api_key=_read_env("OPENAI_API_KEY", "DSP_AI_OPENAI_API_KEY", "OPENAI_API_KEY_5"),
        anthropic_api_key=_read_env("ANTHROPIC_API_KEY", "DSP_AI_ANTHROPIC_API_KEY"),
        gemini_api_key=_read_env("GEMINI_API_KEY", "DSP_AI_GEMINI_API_KEY"),
        deepseek_api_key=_read_env("DEEPSEEK_API_KEY", "DSP_AI_DEEPSEEK_API_KEY"),
        openai_model=_read_env("OPENAI_MODEL", "DSP_AI_OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
        anthropic_model=_read_env("ANTHROPIC_MODEL", "DSP_AI_ANTHROPIC_MODEL")
        or "claude-3-5-sonnet-20241022",
        gemini_model=_read_env("GEMINI_MODEL", "DSP_AI_GEMINI_MODEL") or DEFAULT_GEMINI_MODEL,
        deepseek_model=_read_env("DEEPSEEK_MODEL", "DSP_AI_DEEPSEEK_MODEL")
        or "deepseek-chat",
        request_timeout_seconds=float(_read_env("DSP_AI_LLM_TIMEOUT_SECONDS") or "30"),
        max_retries=int(_read_env("DSP_AI_LLM_MAX_RETRIES") or "2"),
        ai_gateway_api_key=gateway_api_key if gateway_is_valid else None,
        ai_gateway_base_url=gateway_base_url.rstrip("/") if gateway_is_valid else "",
        direct_provider_fallback=(
            _read_env("DSP_AI_DIRECT_PROVIDER_FALLBACK") or "true"
        ).lower()
        in {"1", "true", "yes", "on"},
        provider_mode=provider_mode,
    )
