"""Application-layer execution for the canonical AI research path.

The HTTP router stays provider-agnostic. This service is the composition
boundary that connects the existing DSP ResearchPackage/prompt/validation
chain to the configured OpenAI adapter.

Canonical path:
    ticker/exchange
      -> DSP compose_intelligence
      -> private ResearchPackage
      -> private methodology prompt
      -> OpenAI
      -> JSON draft
      -> DSP validation
      -> PublicResearchReport

No raw provider response, private prompt, provider name, model, or DSP
internals are returned from this service.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from copilot.enums import LanguageModelStatus, UserIntentType
from copilot.models import LanguageModelRequest
from dsp_platform import CompositionInputError, build_composition_request
from dsp_platform.research_package.builder import build_research_package
from dsp_platform.research_prompt import (
    PrivateResearchPromptError,
    build_private_research_prompt,
)
from dsp_platform.research_validation import (
    CanonicalValidationResult,
    CanonicalValidationStatus,
    validate_canonical_research,
)
from llm_adapters import ProviderRegistry, build_default_registry

__all__ = ["ResearchExecution", "execute_research_company"]

_PROVENANCE = ("api_platform.research_company", "dsp.research.openai.v1")


@dataclass(frozen=True, slots=True)
class ResearchExecution:
    """Safe result crossing from application execution to the HTTP layer."""

    ok: bool
    state: str
    outcome: str
    report: dict[str, Any] | None
    limitations: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def execute_research_company(
    *,
    platform: Any,
    ticker: str,
    exchange: str | None,
    company: str | None,
    registry: ProviderRegistry | None = None,
) -> ResearchExecution:
    """Execute the canonical DSP → OpenAI → validation research chain."""
    provider_registry = registry or build_default_registry()
    config = provider_registry.config

    # Product decision: OpenAI only. Other providers remain available to the
    # generic copilot adapter, but are never silently selected for this path.
    if config.default_provider != "openai":
        return ResearchExecution(
            ok=False,
            state="ai_unavailable",
            outcome="ai_unavailable",
            report=None,
            limitations=(
                "Research AI is OpenAI-only. Set DEFAULT_AI_PROVIDER=openai.",
            ),
            errors=("OpenAI research provider is not selected.",),
        )

    adapter = provider_registry.get("openai")
    if adapter is None or not adapter.is_configured():
        return ResearchExecution(
            ok=False,
            state="ai_unavailable",
            outcome="ai_unavailable",
            report=None,
            limitations=(
                "OPENAI_API_KEY is not configured on the backend.",
            ),
            errors=("OpenAI provider unavailable.",),
        )

    try:
        composition_request = build_composition_request(
            ticker=ticker,
            company=company or "",
            exchange=exchange,
            stop_on_stage_failure=False,
        )
    except CompositionInputError as exc:
        return _failed("invalid_input", "invalid_input", str(exc))

    platform_result = platform.compose_intelligence(composition_request)
    pipeline = platform_result.payload
    if pipeline is None:
        return _failed(
            "ai_validation_failed",
            "ai_validation_failed",
            "DSP composition returned no PipelineResult.",
        )

    try:
        package = build_research_package(pipeline, request=composition_request)
        private_prompt = build_private_research_prompt(package)
    except (PrivateResearchPromptError, TypeError, ValueError) as exc:
        return _failed(
            "ai_validation_failed",
            "ai_validation_failed",
            f"DSP research preparation failed: {exc}",
        )

    lm_request = LanguageModelRequest(
        request_id=str(uuid.uuid4()),
        intent_class=UserIntentType.EXPLAIN_REPORT,
        prompt_parts=(
            private_prompt.instructions,
            private_prompt.data_block,
            (
                "Return exactly one JSON object and no Markdown. "
                "Use only fields supported by the canonical AI research schema. "
                "Do not invent missing financial values, scores, entry/exit "
                "prices, scenarios, expected returns, industry data, or evidence. "
                "When DSP does not provide a value, omit that field."
            ),
        ),
        context_digest_ids=(),
        constraints=(
            "DSP ResearchPackage is authoritative for all numerical values.",
            "AI may write explanatory narratives but may not recalculate DSP values.",
            "AI must not invent unavailable data or convert DSP scores to X/10.",
            "Only validated public research may reach the client.",
        ),
        provenance=_PROVENANCE,
    )

    attempts = max(1, provider_registry.config.max_retries + 1)
    lm_result = None
    for _ in range(attempts):
        lm_result = adapter.invoke(lm_request)
        if lm_result.status is LanguageModelStatus.COMPLETE:
            break

    if lm_result is None or lm_result.status is not LanguageModelStatus.COMPLETE:
        limitations = tuple(lm_result.limitations) if lm_result else ()
        return ResearchExecution(
            ok=False,
            state="ai_unavailable",
            outcome="ai_unavailable",
            report=None,
            limitations=limitations or ("OpenAI research invocation failed.",),
            errors=("OpenAI did not return a complete research draft.",),
        )

    raw_text = (lm_result.narrative_text or "").strip()
    try:
        ai_payload = _parse_json_object(raw_text)
    except ValueError as exc:
        return ResearchExecution(
            ok=False,
            state="ai_validation_failed",
            outcome="ai_validation_failed",
            report=None,
            limitations=("OpenAI output was not valid JSON.",),
            errors=(str(exc),),
        )

    validation = validate_canonical_research(package, ai_payload)
    if (
        validation.status is not CanonicalValidationStatus.VALID
        or not validation.ok
    ):
        return _validation_failure(validation)

    report = validation.report.to_public_dict() if validation.report else None
    if not isinstance(report, dict):
        return ResearchExecution(
            ok=False,
            state="ai_validation_failed",
            outcome="ai_validation_failed",
            report=None,
            errors=("DSP validation produced no public report.",),
        )

    limitations = tuple(package.limitations)
    if not pipeline.ok:
        limitations += ("DSP composition completed in degraded mode.",)

    return ResearchExecution(
        ok=True,
        state="ai_executed",
        outcome="success",
        report=report,
        limitations=limitations,
        errors=(),
    )


def _parse_json_object(text: str) -> Mapping[str, Any]:
    if not text:
        raise ValueError("OpenAI returned an empty research draft.")
    candidate = text.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "OpenAI research draft could not be parsed as JSON."
        ) from exc
    if not isinstance(payload, Mapping):
        raise ValueError("OpenAI research draft must be a JSON object.")
    return payload


def _validation_failure(validation: CanonicalValidationResult) -> ResearchExecution:
    issues = tuple(issue.message for issue in validation.issues)
    return ResearchExecution(
        ok=False,
        state="ai_validation_failed",
        outcome="ai_validation_failed",
        report=None,
        limitations=(
            "AI output was rejected by DSP validation; no unverified "
            "conclusion was returned.",
        ),
        errors=issues or ("AI research validation failed.",),
    )


def _failed(state: str, outcome: str, message: str) -> ResearchExecution:
    return ResearchExecution(
        ok=False,
        state=state,
        outcome=outcome,
        report=None,
        errors=(message,),
    )
