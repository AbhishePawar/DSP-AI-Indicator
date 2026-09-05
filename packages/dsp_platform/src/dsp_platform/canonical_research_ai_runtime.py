"""Provider-backed CanonicalResearchAiPort for Gemini web research.

This is a composition seam. Production analyse/protocol factories do not
import it. Default ``activation_ready=False`` keeps execution blocked.

Gemini-specific HTTP stays in llm_adapters. This module maps the
provider-neutral grounded payload onto CanonicalAIDraft.
"""

from __future__ import annotations

import uuid

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.canonical_research_ai.port import (
    CanonicalResearchAiBlockedError,
)
from dsp_platform.research_assembly.models import AI_EXECUTION_BLOCKED
from dsp_platform.research_prompt.models import PrivateResearchPrompt
from dsp_platform.research_validation.models import CanonicalAIResearchOutput
from llm_adapters import (
    ActivationGatedGeminiWebResearch,
    GeminiAdapter,
    untrusted_extraction_from_grounded_web_research,
)

__all__ = ["ProviderBackedCanonicalResearchAiPort"]

_ORIGIN = "canonical_research_ai_runtime"
_PROVENANCE = (
    "dsp_platform.canonical_research_ai_runtime",
    "dsp.llm.gemini.web_research.v1",
)


class ProviderBackedCanonicalResearchAiPort:
    """Interpret a private prompt via Gemini web research.

    Production callers must keep ``activation_ready=False``. This class
    does not calculate valuation, MoS, or recommendation.
    """

    def __init__(
        self,
        adapter: GeminiAdapter,
        *,
        activation_ready: bool = False,
    ) -> None:
        self._gated = ActivationGatedGeminiWebResearch(
            adapter,
            activation_ready=activation_ready,
        )
        self._activation_ready = bool(activation_ready)

    def interpret(self, prompt: PrivateResearchPrompt) -> CanonicalAIDraft:
        if not isinstance(prompt, PrivateResearchPrompt):
            raise CanonicalResearchAiBlockedError(AI_EXECUTION_BLOCKED)
        if not self._activation_ready:
            raise CanonicalResearchAiBlockedError(AI_EXECUTION_BLOCKED)
        request = LanguageModelRequest(
            request_id=str(uuid.uuid4()),
            intent_class=UserIntentType.EXPLAIN_REPORT,
            prompt_parts=(prompt.instructions, prompt.text),
            context_digest_ids=("recommendation",),
            provenance=_PROVENANCE,
            constraints=(
                "Return JSON web_claims only.",
                "Do not invent numbers.",
                "Do not calculate valuation, MoS, or recommendation.",
            ),
        )
        result, grounded = self._gated.invoke_web_research(request)
        if result.status is not LanguageModelStatus.COMPLETE:
            raise CanonicalResearchAiBlockedError(AI_EXECUTION_BLOCKED)
        if grounded.malformed:
            raise CanonicalResearchAiBlockedError(AI_EXECUTION_BLOCKED)
        extraction = untrusted_extraction_from_grounded_web_research(grounded)
        return CanonicalAIDraft(
            output=CanonicalAIResearchOutput(),
            origin=_ORIGIN,
            test_only=False,
            untrusted_extraction=extraction,
        )
