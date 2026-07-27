"""Provider adapter interface — implements copilot LanguageModelPort."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from copilot.models import LanguageModelRequest, LanguageModelResult


@runtime_checkable
class ProviderAdapter(Protocol):
    """Vendor-neutral adapter contract for external LLM providers."""

    provider_id: str
    model_label: str

    def is_configured(self) -> bool:
        """Return True when credentials and configuration are present."""

    def invoke(self, request: LanguageModelRequest) -> LanguageModelResult:
        """Synchronous provider invocation with retry handled by service layer."""

    def stream_invoke(self, request: LanguageModelRequest):
        """Yield narrative text deltas — optional per provider."""
