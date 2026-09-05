"""TEST-ONLY deterministic CanonicalResearchAiPort.

Not a provider adapter. Not production AI. Requires no network, API key,
or SDK. Does not calculate DSP values or mutate ResearchPackage.

Origin: AI_OUTPUT_FIXTURE
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from dsp_platform.canonical_research_ai.models import CanonicalAIDraft
from dsp_platform.research_assembly.models import AI_OUTPUT_FIXTURE
from dsp_platform.research_prompt.models import PrivateResearchPrompt
from dsp_platform.research_validation.models import CanonicalAIResearchOutput

__all__ = [
    "FIXTURE_ORIGIN",
    "TEST_ONLY",
    "DeterministicCanonicalResearchAiPort",
]

TEST_ONLY = True
FIXTURE_ORIGIN = AI_OUTPUT_FIXTURE

_INTERPRETATION_PREFIX = (
    "Interpretation of validated external evidence only; "
    "not a DSP calculation input. "
)


class DeterministicCanonicalResearchAiPort:
    """In-memory test AI. Reads PrivateResearchPrompt.data_block only."""

    TEST_ONLY = True
    origin = FIXTURE_ORIGIN

    def interpret(self, prompt: PrivateResearchPrompt) -> CanonicalAIDraft:
        if not isinstance(prompt, PrivateResearchPrompt):
            raise TypeError(
                "DeterministicCanonicalResearchAiPort requires "
                "PrivateResearchPrompt"
            )
        data = _parse_data_block(prompt.data_block)
        records = _validated_records(data)
        evidence_ids = _dsp_evidence_ids(data)
        interpretation = _interpretation_text(records)
        output = CanonicalAIResearchOutput(
            executive_summary=(
                "DSP canonical data remains authoritative. "
                + interpretation
            ),
            valuation_narrative=(
                "DSP intrinsic value and margin of safety are explained "
                "from supplied DSP evidence only. External evidence is "
                "not used as a valuation input."
            ),
            business_quality_narrative=(
                "Business quality interpretation follows the canonical "
                "DSP score. "
                + interpretation
            ),
            economic_moat_narrative=(
                "Moat interpretation uses the canonical economic-moat "
                "stage. External evidence is supporting context only."
            ),
            management_quality_narrative=(
                "Management interpretation uses the canonical management "
                "stage. "
                + interpretation
            ),
            financial_strength_narrative=(
                "Financial-strength interpretation uses the canonical "
                "stage score."
            ),
            earnings_quality_narrative=(
                "Earnings-quality interpretation uses the canonical "
                "stage score."
            ),
            growth_quality_narrative=(
                "Growth-quality interpretation uses the canonical "
                "stage score."
            ),
            financials_narrative=(
                "Financial metrics are DSP-owned. Validated external "
                "numbers are not canonical financials."
            ),
            buffett_narrative=(
                "Buffett analysis remains existing_pipeline_stages. "
                "No new formula."
            ),
            risk_narrative=(
                "Risk explanation uses DSP ordinal levels. "
                "No numeric risk score."
            ),
            recommendation_narrative=(
                "The DSP recommendation is unchanged and is not replaced."
            ),
            evidence_ids=evidence_ids,
        )
        return CanonicalAIDraft(
            output=output,
            origin=FIXTURE_ORIGIN,
            test_only=True,
        )


def _parse_data_block(data_block: str) -> dict[str, Any]:
    parsed = json.loads(data_block)
    if not isinstance(parsed, dict):
        raise TypeError("private prompt data_block must be a JSON object")
    return parsed


def _validated_records(data: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    payload = data.get("validated_external_evidence")
    if payload is None:
        package = data.get("research_package")
        if isinstance(package, Mapping):
            payload = package.get("external_evidence")
    if not isinstance(payload, Mapping):
        return ()
    rows = payload.get("records") or ()
    if not isinstance(rows, (list, tuple)):
        return ()
    records: list[Mapping[str, Any]] = []
    for item in rows:
        if isinstance(item, Mapping):
            records.append(item)
    return tuple(records)


def _dsp_evidence_ids(data: Mapping[str, Any]) -> tuple[str, ...]:
    package = data.get("research_package")
    if not isinstance(package, Mapping):
        return ("valuation_signals",)
    evidence = package.get("evidence")
    payload = None
    if isinstance(evidence, Mapping):
        payload = evidence.get("payload")
    counts: Mapping[str, Any] = {}
    if isinstance(payload, Mapping):
        raw_counts = payload.get("evidence_counts")
        if isinstance(raw_counts, Mapping):
            counts = raw_counts
    ids = [f"stage:{stage}" for stage in sorted(str(key) for key in counts)]
    identity = package.get("identity")
    if isinstance(identity, Mapping) and identity.get("available"):
        ids.append("identity")
    ids.append("valuation_signals")
    return tuple(ids)


def _interpretation_text(records: tuple[Mapping[str, Any], ...]) -> str:
    if not records:
        return "No validated external evidence was supplied."
    parts: list[str] = [_INTERPRETATION_PREFIX]
    for row in records:
        fact_id = str(row.get("fact_id") or "unknown")
        topic = str(
            row.get("topic") or row.get("evidence_kind") or "supporting"
        )
        excerpt = str(
            row.get("text_value")
            or row.get("evidence_reference")
            or ""
        ).strip()
        parts.append(f"{fact_id} ({topic}): {excerpt}")
    return " ".join(parts)
