"""Provider-neutral model catalog — pricing, capabilities, limits.

Pricing is configuration data, never hard-coded into research logic.
Costs are reported in USD per 1M tokens (input/output) as of public
list prices; these are ESTIMATES, not invoices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """Capability flags advertised by a model."""

    structured_output: bool = False
    tool_call: bool = False
    streaming: bool = True
    reasoning: bool = False


@dataclass(frozen=True, slots=True)
class ModelLimits:
    """Operational limits for a model."""

    context_window_tokens: int
    max_output_tokens: int


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """USD per 1M tokens (input, output)."""

    input_usd_per_1m: float
    output_usd_per_1m: float


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """Provider-neutral model identity."""

    provider: str
    model: str
    capabilities: ModelCapabilities
    limits: ModelLimits
    pricing: ModelPricing
    notes: str = ""

    @property
    def identity(self) -> str:
        return f"{self.provider}:{self.model}"


# Default catalog. Pricing is configuration data; tests may override.
# Sources (Jan 2026 public list prices — verify before production):
# - OpenAI gpt-4o-mini: $0.15 / $0.60 per 1M
# - Anthropic claude-3-5-sonnet: $3.00 / $15.00 per 1M
# - Gemini 1.5 Flash: $0.075 / $0.30 per 1M
# - DeepSeek chat: $0.14 / $0.28 per 1M (cache miss pricing)
DEFAULT_CATALOG: Mapping[str, ModelInfo] = {
    "openai:gpt-4o-mini": ModelInfo(
        provider="openai",
        model="gpt-4o-mini",
        capabilities=ModelCapabilities(
            structured_output=True, tool_call=True, streaming=True
        ),
        limits=ModelLimits(context_window_tokens=128_000, max_output_tokens=16_384),
        pricing=ModelPricing(input_usd_per_1m=0.15, output_usd_per_1m=0.60),
        notes="Default OpenAI workhorse in current llm_adapters.",
    ),
    "anthropic:claude-3-5-sonnet-20241022": ModelInfo(
        provider="anthropic",
        model="claude-3-5-sonnet-20241022",
        capabilities=ModelCapabilities(
            structured_output=True, tool_call=True, streaming=True
        ),
        limits=ModelLimits(context_window_tokens=200_000, max_output_tokens=8_192),
        pricing=ModelPricing(input_usd_per_1m=3.00, output_usd_per_1m=15.00),
        notes="Stub adapter in llm_adapters today.",
    ),
    "gemini:gemini-1.5-flash": ModelInfo(
        provider="gemini",
        model="gemini-1.5-flash",
        capabilities=ModelCapabilities(
            structured_output=True, tool_call=True, streaming=True
        ),
        limits=ModelLimits(context_window_tokens=1_000_000, max_output_tokens=8_192),
        pricing=ModelPricing(input_usd_per_1m=0.075, output_usd_per_1m=0.30),
        notes="Cheapest tier; stub adapter in llm_adapters today.",
    ),
    "deepseek:deepseek-chat": ModelInfo(
        provider="deepseek",
        model="deepseek-chat",
        capabilities=ModelCapabilities(
            structured_output=True, tool_call=True, streaming=True
        ),
        limits=ModelLimits(context_window_tokens=64_000, max_output_tokens=8_000),
        pricing=ModelPricing(input_usd_per_1m=0.14, output_usd_per_1m=0.28),
        notes="DeepSeek V3 chat tier; not yet wired in llm_adapters.",
    ),
}


def get_model_info(identity: str, catalog: Mapping[str, ModelInfo] | None = None) -> ModelInfo:
    """Resolve ``provider:model`` to its ModelInfo, else raise KeyError."""
    src = catalog if catalog is not None else DEFAULT_CATALOG
    if identity not in src:
        raise KeyError(f"Unknown model identity: {identity!r}")
    return src[identity]


def list_identities(catalog: Mapping[str, ModelInfo] | None = None) -> tuple[str, ...]:
    """Return all configured ``provider:model`` identities."""
    src = catalog if catalog is not None else DEFAULT_CATALOG
    return tuple(sorted(src.keys()))


__all__ = [
    "DEFAULT_CATALOG",
    "ModelCapabilities",
    "ModelInfo",
    "ModelLimits",
    "ModelPricing",
    "get_model_info",
    "list_identities",
]
