"""AI-assisted web discovery behind the existing activation/blocked gate.

Production must pass activation_ready=False. This module does not select
a vendor, does not read environment flags, and does not call HTTP.
"""

from __future__ import annotations

from dsp_platform.canonical_research_ai.port import (
    CanonicalResearchAiBlockedError,
    CanonicalResearchAiPort,
)
from dsp_platform.current_outstanding_protocol.prompt import (
    build_share_count_web_research_prompt,
)
from dsp_platform.current_outstanding_protocol.web_research import (
    discovery_result_from_untrusted_web_claims,
    untrusted_web_claims_from_ai_draft,
)
from dsp_platform.external_evidence_discovery.models import (
    DISCOVERY_NOT_CONFIGURED,
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)
from dsp_platform.external_evidence_discovery.port import (
    ExternalEvidenceDiscoveryBlockedError,
    ExternalEvidenceDiscoveryPort,
    validate_discovery_request,
)

__all__ = [
    "ActivationGatedEvidenceDiscovery",
    "AiAssistedShareCountWebDiscovery",
]


class ActivationGatedEvidenceDiscovery:
    """Refuse discovery unless the caller already proved activation ready.

    ``activation_ready`` is injected by the composition root after the
    existing activation guard. It is never read from the environment.
    """

    def __init__(
        self,
        inner: ExternalEvidenceDiscoveryPort,
        *,
        activation_ready: bool,
    ) -> None:
        self._inner = inner
        self._activation_ready = bool(activation_ready)

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        if not self._activation_ready:
            raise ExternalEvidenceDiscoveryBlockedError(DISCOVERY_NOT_CONFIGURED)
        return self._inner.discover(request)


class AiAssistedShareCountWebDiscovery:
    """Ask CanonicalResearchAiPort for untrusted locators. T3 only."""

    def __init__(self, ai: CanonicalResearchAiPort) -> None:
        self._ai = ai

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        validate_discovery_request(request)
        prompt = build_share_count_web_research_prompt(request)
        try:
            draft = self._ai.interpret(prompt)
        except CanonicalResearchAiBlockedError as exc:
            raise ExternalEvidenceDiscoveryBlockedError(str(exc)) from exc
        claims = untrusted_web_claims_from_ai_draft(draft)
        return discovery_result_from_untrusted_web_claims(request, claims)
