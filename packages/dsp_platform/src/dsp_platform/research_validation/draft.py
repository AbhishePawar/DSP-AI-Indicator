"""Provider-neutral CanonicalAIDraft — pre-validation AI intake.

Uses the existing ``ALLOWED_AI_FIELD_NAMES`` / ``CanonicalAIResearchOutput``
schema. Does not invent a second field list. Extra keys fail closed.
Private provider/prompt metadata is never accepted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from typing import Any

from dsp_platform.research_package.models import PRIVATE_FIELD_NAMES
from dsp_platform.research_report.moat_presentation import CANONICAL_MOAT_DIMENSIONS
from dsp_platform.research_report.models import PRIVATE_REPORT_FIELD_NAMES
from dsp_platform.research_validation.models import (
    ALLOWED_AI_FIELD_NAMES,
    CanonicalAIResearchOutput,
)

__all__ = [
    "CanonicalAIDraft",
    "CanonicalAIDraftError",
    "parse_canonical_ai_draft",
]

_NARRATIVE_FIELDS = frozenset(
    {
        "executive_summary",
        "valuation_narrative",
        "business_quality_narrative",
        "economic_moat_narrative",
        "management_quality_narrative",
        "financial_strength_narrative",
        "earnings_quality_narrative",
        "growth_quality_narrative",
        "financials_narrative",
        "buffett_narrative",
        "risk_narrative",
        "recommendation_narrative",
        "buffett_methodology",
        "recommendation_action",
        "score_10_status",
    }
)
_NUMBER_FIELDS = frozenset(
    {
        "current_price",
        "intrinsic_value",
        "intrinsic_value_per_share",
        "valuation_range_low",
        "valuation_range_mid",
        "valuation_range_high",
        "margin_of_safety",
        "buffett_overall_score_100",
        "circle_of_competence_score",
        "recommendation_score_100",
        "entry_price",
        "buy_price",
        "target_price",
        "exit_price",
        "stop_loss",
        "entry_zone",
        "expected_return",
        "expected_returns",
        "forward_cagr",
        "forecast_cagr",
    }
)
_NUMBER_MAP_FIELDS = frozenset({"financial_metrics", "quality_scores"})
_MAPPING_FIELDS = frozenset({"buffett_weights", "scenarios"})
_MOAT_INTERPRETATION_KEYS = frozenset({"narrative", "durability", "threats"})
_PRIVATE_INTAKE_KEYS = PRIVATE_FIELD_NAMES | PRIVATE_REPORT_FIELD_NAMES | frozenset(
    {
        "activation_evidence",
        "activation_reasons",
        "recommended_models",
        "request_id",
        "request_ids",
        "data_block",
        "methodology_canary",
        "system_prompt",
        "chain_of_thought",
        "tool_internals",
        "raw_provider_response",
    }
)


class CanonicalAIDraftError(ValueError):
    """Fail-closed intake error. Not a public HTTP type."""


@dataclass(frozen=True, slots=True, repr=False)
class CanonicalAIDraft:
    """Strict pre-validation AI interpretation. Not an HTTP/client DTO."""

    _output: CanonicalAIResearchOutput
    _keys: frozenset[str]

    def to_canonical_output(self) -> CanonicalAIResearchOutput:
        return self._output

    def provided_keys(self) -> frozenset[str]:
        return self._keys

    def __repr__(self) -> str:
        return "CanonicalAIDraft(<redacted>)"


def parse_canonical_ai_draft(payload: object) -> CanonicalAIDraft:
    """Parse a mapping into ``CanonicalAIDraft``. Extra keys fail closed."""
    if not isinstance(payload, Mapping):
        raise CanonicalAIDraftError("CanonicalAIDraft requires a mapping")
    keys = {str(key) for key in payload}
    private = sorted(keys & _PRIVATE_INTAKE_KEYS)
    if private:
        raise CanonicalAIDraftError(
            "CanonicalAIDraft rejects private fields: " + ", ".join(private)
        )
    unknown = sorted(keys - ALLOWED_AI_FIELD_NAMES)
    if unknown:
        raise CanonicalAIDraftError(
            "CanonicalAIDraft rejects unknown fields: " + ", ".join(unknown)
        )
    typed: dict[str, Any] = {}
    for key in keys:
        typed[key] = _require_typed(key, payload[key])
    output = _to_output(typed)
    return CanonicalAIDraft(_output=output, _keys=frozenset(keys))


def _require_typed(key: str, value: object) -> object:
    if value is None:
        return None
    if key in _NARRATIVE_FIELDS:
        if not isinstance(value, str):
            raise CanonicalAIDraftError(f"{key} must be a string")
        return value
    if key in _NUMBER_FIELDS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CanonicalAIDraftError(f"{key} must be a number")
        return float(value)
    if key in _NUMBER_MAP_FIELDS:
        if not isinstance(value, Mapping):
            raise CanonicalAIDraftError(f"{key} must be a mapping")
        out: dict[str, float | None] = {}
        for nested_key, nested in value.items():
            if nested is None:
                out[str(nested_key)] = None
            elif isinstance(nested, bool) or not isinstance(nested, (int, float)):
                raise CanonicalAIDraftError(f"{key} values must be numbers")
            else:
                out[str(nested_key)] = float(nested)
        return out
    if key in _MAPPING_FIELDS:
        if not isinstance(value, Mapping):
            raise CanonicalAIDraftError(f"{key} must be a mapping")
        return {str(nested_key): nested for nested_key, nested in value.items()}
    if key == "evidence_ids":
        message = "evidence_ids must be a sequence of strings"
        if isinstance(value, str):
            raise CanonicalAIDraftError(message)
        if not isinstance(value, Sequence):
            raise CanonicalAIDraftError(message)
        ids = []
        for item in value:
            if not isinstance(item, str):
                raise CanonicalAIDraftError(message)
            ids.append(item)
        return tuple(ids)
    if key == "score_10":
        if isinstance(value, bool):
            raise CanonicalAIDraftError("score_10 must be a number or mapping")
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, Mapping):
            return {str(nested_key): nested for nested_key, nested in value.items()}
        raise CanonicalAIDraftError("score_10 must be a number or mapping")
    if key == "economic_moat_dimension_interpretations":
        return _require_moat_interpretations(value)
    raise CanonicalAIDraftError(f"{key} has an unsupported type")


def _require_moat_interpretations(value: object) -> dict[str, dict[str, str]]:
    if not isinstance(value, Mapping):
        raise CanonicalAIDraftError(
            "economic_moat_dimension_interpretations must be a mapping"
        )
    allowed = set(CANONICAL_MOAT_DIMENSIONS)
    out: dict[str, dict[str, str]] = {}
    for raw_key, raw_item in value.items():
        identifier = str(raw_key)
        if identifier not in allowed:
            raise CanonicalAIDraftError(
                "economic_moat_dimension_interpretations rejects identifier "
                f"{identifier}"
            )
        if isinstance(raw_item, str):
            text = raw_item.strip()
            if text:
                out[identifier] = {"narrative": text}
            continue
        if not isinstance(raw_item, Mapping):
            raise CanonicalAIDraftError(
                "economic_moat_dimension_interpretations values must be "
                "strings or mappings"
            )
        nested: dict[str, str] = {}
        for nested_key, nested_value in raw_item.items():
            name = str(nested_key)
            if name not in _MOAT_INTERPRETATION_KEYS:
                raise CanonicalAIDraftError(
                    "economic_moat_dimension_interpretations rejects field "
                    f"{name}"
                )
            if not isinstance(nested_value, str):
                raise CanonicalAIDraftError(
                    "economic_moat_dimension_interpretations text must be "
                    "a string"
                )
            text = nested_value.strip()
            if text:
                nested[name] = text
        if nested:
            out[identifier] = nested
    return out


def _to_output(payload: Mapping[str, Any]) -> CanonicalAIResearchOutput:
    iv = payload.get("intrinsic_value")
    ivps = payload.get("intrinsic_value_per_share")
    if iv is not None and ivps is not None and iv != ivps:
        raise CanonicalAIDraftError(
            "intrinsic_value and intrinsic_value_per_share must match"
        )
    if iv is None:
        iv = ivps
    kwargs: dict[str, Any] = {}
    names = {item.name for item in fields(CanonicalAIResearchOutput)}
    for key, value in payload.items():
        if key == "intrinsic_value_per_share":
            continue
        if key in names:
            kwargs[key] = value
    if iv is not None:
        kwargs["intrinsic_value"] = iv
    return CanonicalAIResearchOutput(**kwargs)
