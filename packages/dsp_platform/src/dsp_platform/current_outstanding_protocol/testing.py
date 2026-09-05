"""TEST-ONLY deterministic share-count extraction AI.

Not a provider adapter. Not production AI. Makes no network calls.
Does not construct ShareCountSnapshot or call DSP acceptance.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.current_outstanding_protocol.currentness import (
    CorporateActionCurrentnessEvidence,
)
from dsp_platform.current_outstanding_protocol.web_research import (
    UntrustedWebEvidenceClaim,
    discovery_result_from_untrusted_web_claims,
)
from dsp_platform.external_evidence_discovery.models import (
    ExternalEvidenceDiscoveryRequest,
    ExternalEvidenceDiscoveryResult,
)
from dsp_platform.external_evidence_discovery.port import validate_discovery_request
from dsp_platform.research_assembly.models import AI_OUTPUT_FIXTURE
from dsp_platform.research_prompt.models import PrivateResearchPrompt
from dsp_platform.research_validation.models import CanonicalAIResearchOutput

__all__ = [
    "FIXTURE_ORIGIN",
    "SCREENER_FIXTURE_URL",
    "TEST_ONLY",
    "DeterministicScreenerLikeWebDiscovery",
    "DeterministicShareCountExtractionAiPort",
    "DeterministicShareCountWebResearchAiPort",
    "fixture_option_b_currentness",
]

TEST_ONLY = True
FIXTURE_ORIGIN = AI_OUTPUT_FIXTURE

_SHARE_COUNT = re.compile(
    r"(?P<value>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<frac>\d+))?\s+shares\b",
    re.IGNORECASE,
)


class DeterministicShareCountExtractionAiPort:
    """In-memory extraction double. Origin remains AI_OUTPUT_FIXTURE."""

    TEST_ONLY = True
    origin = FIXTURE_ORIGIN

    def __init__(self, extraction: Mapping[str, Any] | None = None) -> None:
        self._extraction = None if extraction is None else dict(extraction)
        self._override = extraction is not None

    def interpret(self, prompt: PrivateResearchPrompt) -> CanonicalAIDraft:
        if not isinstance(prompt, PrivateResearchPrompt):
            raise TypeError(
                "DeterministicShareCountExtractionAiPort requires "
                "PrivateResearchPrompt"
            )
        payload = self._extraction if self._override else _from_prompt(prompt)
        output = CanonicalAIResearchOutput(
            executive_summary=(
                "Untrusted share-count extraction only. DSP remains the "
                "sole authority for validation and calculation."
            ),
            valuation_narrative=(
                "DSP intrinsic value is not calculated by this extraction."
            ),
            recommendation_narrative=(
                "DSP recommendation is unchanged and is not replaced."
            ),
        )
        return CanonicalAIDraft(
            output=output,
            origin=FIXTURE_ORIGIN,
            test_only=True,
            untrusted_extraction=payload,
        )


def _from_prompt(prompt: PrivateResearchPrompt) -> dict[str, Any] | None:
    parsed = json.loads(prompt.data_block)
    if not isinstance(parsed, Mapping):
        return None
    identity = parsed.get("identity")
    symbol = ""
    if isinstance(identity, Mapping):
        symbol = str(identity.get("symbol") or "").strip()
    text = str(parsed.get("text") or "")
    match = _SHARE_COUNT.search(text)
    if match is None or not symbol:
        return None
    raw = match.group("value").replace(",", "")
    frac = match.group("frac")
    count = f"{raw}.{frac}" if frac is not None else raw
    excerpt = ""
    for line in text.splitlines():
        lowered = line.lower()
        if "outstanding" in lowered and "shares" in lowered:
            excerpt = line.strip()
            break
    if not excerpt:
        return None
    as_of = parsed.get("as_of")
    if not as_of:
        header = re.search(r"Fact-As-Of:\s*(\d{4}-\d{2}-\d{2})", text)
        iso = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
        as_of = header.group(1) if header else (iso.group(1) if iso else None)
    return {
        "company_identity": symbol,
        "claimed_share_count": count,
        "unit": "shares",
        "as_of_date": as_of,
        "source_reference": parsed.get("locator"),
        "evidence_reference": excerpt,
        "supporting_excerpt": excerpt,
    }


SCREENER_FIXTURE_URL = "https://www.screener.in/company/DSPX/consolidated/"
_SCREENER_EXCERPT = (
    "Screener lists current shares outstanding for DSPX as of 31 March 2024."
)


class DeterministicShareCountWebResearchAiPort:
    """TEST-ONLY untrusted web_claims. No network. Not production AI."""

    TEST_ONLY = True
    origin = FIXTURE_ORIGIN

    def __init__(self, web_claims: tuple[Mapping[str, Any], ...] = ()) -> None:
        self._web_claims = tuple(dict(row) for row in web_claims)

    def interpret(self, prompt: PrivateResearchPrompt) -> CanonicalAIDraft:
        if not isinstance(prompt, PrivateResearchPrompt):
            raise TypeError(
                "DeterministicShareCountWebResearchAiPort requires "
                "PrivateResearchPrompt"
            )
        output = CanonicalAIResearchOutput(
            executive_summary=(
                "Untrusted web locators only. DSP remains the sole authority."
            ),
            valuation_narrative="DSP valuation is not calculated here.",
            recommendation_narrative="DSP recommendation is unchanged.",
        )
        return CanonicalAIDraft(
            output=output,
            origin=FIXTURE_ORIGIN,
            test_only=True,
            untrusted_extraction={"web_claims": list(self._web_claims)},
        )


class DeterministicScreenerLikeWebDiscovery:
    """TEST-ONLY Screener-like T3 locator. Never selected by production."""

    TEST_ONLY = True

    def discover(
        self, request: ExternalEvidenceDiscoveryRequest
    ) -> ExternalEvidenceDiscoveryResult:
        validate_discovery_request(request)
        claim = UntrustedWebEvidenceClaim(
            company_identity=request.identity.symbol,
            source_url=SCREENER_FIXTURE_URL,
            evidence_excerpt=_SCREENER_EXCERPT,
            claimed_share_count=100,
            unit="shares",
            as_of="2024-03-31",
            ticker=request.identity.symbol,
            exchange=request.identity.exchange or "",
            source_name="Screener",
            source_type="company_website",
            evidence_reference=_SCREENER_EXCERPT,
            explanation="Screener page appears to list current outstanding shares.",
        )
        return discovery_result_from_untrusted_web_claims(request, (claim,))


def fixture_option_b_currentness(
    *,
    as_of,
    retrieved_at,
) -> CorporateActionCurrentnessEvidence:
    """TEST-ONLY complete CA set: no later share-changing event."""
    horizon = retrieved_at.date()
    return CorporateActionCurrentnessEvidence(
        events=(),
        complete_through=horizon,
        share_count_as_of=as_of,
        source_tier="TIER_1_PRIMARY",
        source_url="https://fixtures.dsp.test/corporate-actions/complete",
        evidence_reference=(
            "Fixture corporate-action corpus is complete through the "
            "retrieval date with no later share-changing event."
        ),
    )

