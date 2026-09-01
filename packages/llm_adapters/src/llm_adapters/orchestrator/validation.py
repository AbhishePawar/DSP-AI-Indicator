"""Validation pipeline for AI research output.

AI response → schema → required sections → evidence refs → unsupported
claims → privacy → pack construction. Critical failures fail closed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from pydantic import ValidationError

from llm_adapters.evaluation import ErrorCategory
from llm_adapters.orchestrator.research_prompt import PRIVATE_PROMPT_CANARY
from llm_adapters.orchestrator.schema import (
    AIResearchOutput,
    EVIDENCE_REQUIRED_SECTIONS,
    REQUIRED_SECTIONS,
)
from llm_adapters.orchestrator.evidence import ok_payload, outcomes_by_tool
from llm_adapters.privacy_boundary import (
    PublicDecisionPack,
    assert_no_private_leakage,
)
from llm_adapters.tools.protocol.models import ToolCallOutcome, ToolCallStatus
from llm_adapters.tools.protocol.privacy import ProtocolPrivacyError, assert_provider_envelope_private_free


class ValidationFailureKind(str, Enum):
    MALFORMED_OUTPUT = "malformed_output"
    MISSING_SECTION = "missing_section"
    MISSING_EVIDENCE = "missing_evidence"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    PRIVACY = "privacy"
    TOOL_UNAVAILABLE = "tool_unavailable"


@dataclass(frozen=True, slots=True)
class ValidationFailure:
    kind: ValidationFailureKind
    message: str
    error_category: ErrorCategory


@dataclass(frozen=True, slots=True)
class ValidationSuccess:
    output: AIResearchOutput
    pack: PublicDecisionPack


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?")

_PRIVATE_SUBSTRINGS = (
    PRIVATE_PROMPT_CANARY,
    "routing_tier",
    "routing_reasons",
    "internal_prompt",
    "chain_of_thought",
    "api_key",
    "input_tokens",
    "output_tokens",
    "estimated_cost",
)

SECTION_TOOL: dict[str, str] = {
    "valuation": "dsp.valuation",
    "business_quality": "dsp.business_quality",
    "moat": "dsp.economic_moat",
    "management": "dsp.management_quality",
    "financial_strength": "dsp.financial_strength",
    "earnings_quality": "dsp.earnings_quality",
    "growth_quality": "dsp.growth_quality",
    "risk": "dsp.risk",
}


def extract_json_object(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    fenced = _JSON_FENCE.search(text)
    if fenced:
        text = fenced.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    return text[start : end + 1]


def parse_structured_output(raw: str | None) -> AIResearchOutput | ValidationFailure:
    if not raw or not raw.strip():
        return ValidationFailure(
            kind=ValidationFailureKind.MALFORMED_OUTPUT,
            message="empty AI output",
            error_category=ErrorCategory.MALFORMED_OUTPUT,
        )
    blob = extract_json_object(raw)
    if blob is None:
        return ValidationFailure(
            kind=ValidationFailureKind.MALFORMED_OUTPUT,
            message="AI output is not JSON",
            error_category=ErrorCategory.MALFORMED_OUTPUT,
        )
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return ValidationFailure(
            kind=ValidationFailureKind.MALFORMED_OUTPUT,
            message="AI JSON is malformed",
            error_category=ErrorCategory.MALFORMED_OUTPUT,
        )
    if not isinstance(data, dict):
        return ValidationFailure(
            kind=ValidationFailureKind.MALFORMED_OUTPUT,
            message="AI JSON must be an object",
            error_category=ErrorCategory.MALFORMED_OUTPUT,
        )
    try:
        return AIResearchOutput.model_validate(data)
    except ValidationError:
        return ValidationFailure(
            kind=ValidationFailureKind.MALFORMED_OUTPUT,
            message="AI output failed schema validation",
            error_category=ErrorCategory.SCHEMA_FAILURE,
        )


def _fail(kind: ValidationFailureKind, message: str, category: ErrorCategory) -> ValidationFailure:
    return ValidationFailure(kind=kind, message=message, error_category=category)


def validate_research_output(
    raw: str | None,
    *,
    outcomes: tuple[ToolCallOutcome, ...],
    catalog: tuple[dict[str, Any], ...],
) -> ValidationSuccess | ValidationFailure:
    parsed = parse_structured_output(raw)
    if isinstance(parsed, ValidationFailure):
        return parsed
    output = parsed

    missing = [name for name in REQUIRED_SECTIONS if name not in output.section_map()]
    if missing:
        return _fail(
            ValidationFailureKind.MISSING_SECTION,
            "required research sections missing",
            ErrorCategory.SCHEMA_FAILURE,
        )

    catalog_ids = {str(item["id"]) for item in catalog}
    catalog_by_id = {str(item["id"]): item for item in catalog}
    by_tool = outcomes_by_tool(outcomes)

    for section_name, section in output.section_map().items():
        if section_name in EVIDENCE_REQUIRED_SECTIONS and not section.unavailable:
            if not section.evidence_ids:
                return _fail(
                    ValidationFailureKind.MISSING_EVIDENCE,
                    f"section {section_name} has no evidence",
                    ErrorCategory.MISSING_EVIDENCE,
                )
        for evidence_id in section.evidence_ids:
            if evidence_id not in catalog_ids:
                return _fail(
                    ValidationFailureKind.UNSUPPORTED_CLAIM,
                    "evidence id is not in the catalog",
                    ErrorCategory.CITATION_FAILURE,
                )

    for item in output.evidence:
        if item.id not in catalog_ids:
            return _fail(
                ValidationFailureKind.UNSUPPORTED_CLAIM,
                "fabricated evidence citation",
                ErrorCategory.CITATION_FAILURE,
            )
        catalog_row = catalog_by_id[item.id]
        if item.source != catalog_row.get("tool_name"):
            return _fail(
                ValidationFailureKind.UNSUPPORTED_CLAIM,
                "evidence source does not match the tool",
                ErrorCategory.CITATION_FAILURE,
            )
        outcome = by_tool.get(item.source)
        if outcome is None or outcome.status is not ToolCallStatus.OK:
            return _fail(
                ValidationFailureKind.UNSUPPORTED_CLAIM,
                "citation refers to a failed or missing tool",
                ErrorCategory.UNSUPPORTED_CLAIM,
            )

    rec_outcome = by_tool.get("dsp.investment_recommendation")
    rec_payload = ok_payload(rec_outcome)
    if rec_payload is None:
        return _fail(
            ValidationFailureKind.TOOL_UNAVAILABLE,
            "investment recommendation unavailable",
            ErrorCategory.TOOL_FAILURE,
        )
    dsp_decision = str(rec_payload.get("decision") or "").strip()
    if not dsp_decision:
        return _fail(
            ValidationFailureKind.TOOL_UNAVAILABLE,
            "investment recommendation missing decision",
            ErrorCategory.TOOL_FAILURE,
        )
    if output.recommendation.strip().lower() != dsp_decision.lower():
        return _fail(
            ValidationFailureKind.UNSUPPORTED_CLAIM,
            "AI recommendation does not match DSP tool",
            ErrorCategory.UNSUPPORTED_CLAIM,
        )

    val_outcome = by_tool.get("dsp.valuation")
    val_payload = ok_payload(val_outcome)
    if val_payload is None:
        if not output.valuation.unavailable:
            return _fail(
                ValidationFailureKind.UNSUPPORTED_CLAIM,
                "valuation tool unavailable but AI presented a valuation",
                ErrorCategory.UNSUPPORTED_CLAIM,
            )
    else:
        if output.valuation.unavailable:
            return _fail(
                ValidationFailureKind.UNSUPPORTED_CLAIM,
                "valuation tool succeeded but AI marked unavailable",
                ErrorCategory.UNSUPPORTED_CLAIM,
            )
        iv = val_payload.get("intrinsic_value_per_share")
        if iv is not None:
            summary_numbers = set(_NUMBER.findall(output.valuation.summary))
            known = {_format_number(iv)}
            mos = ok_payload(by_tool.get("dsp.margin_of_safety"))
            if mos and mos.get("margin_of_safety") is not None:
                known.add(_format_number(mos["margin_of_safety"]))
            if rec_payload.get("confidence") is not None:
                known.add(_format_number(rec_payload["confidence"]))
            invented = {n for n in summary_numbers if n not in known and not _is_trivial_number(n)}
            # Allow the canonical IV to appear; reject unrelated invented figures.
            if invented and _format_number(iv) not in summary_numbers:
                return _fail(
                    ValidationFailureKind.UNSUPPORTED_CLAIM,
                    "valuation summary does not cite the DSP intrinsic value",
                    ErrorCategory.UNSUPPORTED_CLAIM,
                )

    privacy_fail = _privacy_scan(output)
    if privacy_fail is not None:
        return privacy_fail

    pack = _build_public_pack(output, rec_payload, val_payload)
    try:
        assert_no_private_leakage(pack.to_dict())
        assert_provider_envelope_private_free(pack.to_dict())
    except (ValueError, ProtocolPrivacyError):
        return _fail(
            ValidationFailureKind.PRIVACY,
            "public pack failed privacy validation",
            ErrorCategory.UNKNOWN,
        )
    dumped = json.dumps(pack.to_dict())
    if PRIVATE_PROMPT_CANARY in dumped:
        return _fail(
            ValidationFailureKind.PRIVACY,
            "private prompt leaked into public pack",
            ErrorCategory.UNKNOWN,
        )
    return ValidationSuccess(output=output, pack=pack)


def failed_closed_pack() -> PublicDecisionPack:
    """Honest public pack when research cannot complete. No fabricated decision."""
    pack = PublicDecisionPack(
        recommendation="Unable to complete.",
        valuation=None,
        analysis="Research could not be completed from authenticated evidence.",
        risks=(),
        evidence_citations=(),
        confidence=0.0,
        limitations=("research_failed_closed",),
    )
    assert_no_private_leakage(pack.to_dict())
    return pack


def _build_public_pack(
    output: AIResearchOutput,
    rec_payload: Mapping[str, Any],
    val_payload: Mapping[str, Any] | None,
) -> PublicDecisionPack:
    iv = None if val_payload is None else val_payload.get("intrinsic_value_per_share")
    valuation = None if iv is None else str(iv)
    citations = tuple(dict.fromkeys(item.id for item in output.evidence))
    risks: tuple[str, ...]
    if output.risk.unavailable:
        risks = ()
    else:
        risks = (output.risk.summary,)
    public_limitations = tuple(
        item
        for item in output.limitations
        if not any(token in item.lower() for token in _PRIVATE_SUBSTRINGS)
    )
    return PublicDecisionPack(
        recommendation=str(rec_payload.get("decision")),
        valuation=valuation,
        analysis=output.decision_brief,
        risks=risks,
        evidence_citations=citations,
        confidence=float(output.confidence),
        limitations=public_limitations or ("none",),
    )


def _privacy_scan(output: AIResearchOutput) -> ValidationFailure | None:
    blob = output.model_dump()
    try:
        assert_provider_envelope_private_free({"result": blob, "tool_name": "orchestrator"})
    except (ProtocolPrivacyError, ValueError):
        return _fail(
            ValidationFailureKind.PRIVACY,
            "AI output failed privacy validation",
            ErrorCategory.UNKNOWN,
        )
    text = json.dumps(blob)
    if PRIVATE_PROMPT_CANARY in text:
        return _fail(
            ValidationFailureKind.PRIVACY,
            "private prompt echoed in AI output",
            ErrorCategory.UNKNOWN,
        )
    lowered = text.lower()
    for token in ("api_key", "chain_of_thought", "routing_reasons", "internal_prompt"):
        if token in lowered:
            return _fail(
                ValidationFailureKind.PRIVACY,
                "private field echoed in AI output",
                ErrorCategory.UNKNOWN,
            )
    return None


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return str(number)


def _is_trivial_number(text: str) -> bool:
    try:
        number = float(text)
    except ValueError:
        return False
    return number in {0.0, 1.0}


__all__ = [
    "ValidationFailure",
    "ValidationFailureKind",
    "ValidationSuccess",
    "extract_json_object",
    "failed_closed_pack",
    "parse_structured_output",
    "validate_research_output",
]
