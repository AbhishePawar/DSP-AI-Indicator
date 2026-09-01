"""Validate AI research drafts against ResearchPackage DSP truth.

Aggregator/comparison only. Does not calculate valuation, scores, X/10,
entry/exit, scenarios, or expected returns. Does not call AI, HTTP, or
DSP engines.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import fields, replace
from typing import Any

from dsp_platform.research_package.models import (
    SOURCE_PIPELINE_COMPOSE_INTELLIGENCE,
    ResearchPackage,
    contains_private_fields,
)
from dsp_platform.research_prompt.methodology import PRIVATE_METHODOLOGY_CANARY
from dsp_platform.research_report.builder import build_public_research_report
from dsp_platform.research_report.models import (
    BUFFETT_METHODOLOGY,
    PRIVATE_REPORT_FIELD_NAMES,
    SCORE_10_STATUS,
    AiNarrative,
    PublicResearchReport,
    QualityFactorPublic,
    assert_public_report_privacy,
    empty_ai_narrative,
)
from dsp_platform.research_validation.models import (
    ALLOWED_AI_FIELD_NAMES,
    CanonicalAIResearchOutput,
    CanonicalValidationIssue,
    CanonicalValidationKind,
    CanonicalValidationResult,
    CanonicalValidationStatus,
)

__all__ = ["validate_canonical_research"]

_OLD_TOOL_LOOP_CANARY = "DSP_PRIVATE_RESEARCH_INSTRUCTION_v1"
_CANARIES = (PRIVATE_METHODOLOGY_CANARY, _OLD_TOOL_LOOP_CANARY)

_X10_IN_TEXT = re.compile(r"\b\d{1,2}(?:\.\d+)?\s*/\s*10\b")

_ENTRY_EXIT_FIELDS = (
    "entry_price",
    "buy_price",
    "target_price",
    "exit_price",
    "stop_loss",
    "entry_zone",
)

_EXPECTED_RETURN_FIELDS = (
    "expected_return",
    "expected_returns",
    "forward_cagr",
    "forecast_cagr",
)

_QUALITY_ATTRS = (
    "business_quality",
    "economic_moat",
    "management_quality",
    "financial_strength",
    "earnings_quality",
    "growth_quality",
)

_MATERIAL_NARRATIVES = (
    "valuation_narrative",
    "business_quality_narrative",
    "risk_narrative",
    "buffett_narrative",
)

_NARRATIVE_FIELDS = (
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
)

_PRIVACY_TEXT_TOKENS = (
    "api_key",
    "chain_of_thought",
    "internal_prompt",
    "private_prompt",
    "system_prompt",
    "raw_ai_response",
    "routing_tier",
    "routing_reasons",
)

_ABS_TOL = 1e-9


def validate_canonical_research(
    research_package: object,
    ai_output: CanonicalAIResearchOutput | Mapping[str, Any],
) -> CanonicalValidationResult:
    """Fail-closed validation of an AI draft against ResearchPackage."""
    package = _require_package(research_package)
    if isinstance(package, CanonicalValidationResult):
        return package
    parsed = _parse_ai_output(ai_output)
    if isinstance(parsed, CanonicalValidationResult):
        return parsed
    output, provided = parsed
    dsp_report = build_public_research_report(package)
    issues: list[CanonicalValidationIssue] = []
    issues.extend(_privacy_and_canary(output, provided))
    issues.extend(_numerical_integrity(output, provided, dsp_report))
    issues.extend(_recommendation_integrity(output, provided, dsp_report))
    issues.extend(_buffett_integrity(output, provided, dsp_report))
    issues.extend(_score_10_integrity(output, provided))
    issues.extend(_entry_exit_integrity(provided))
    issues.extend(_scenario_integrity(provided))
    issues.extend(_expected_return_integrity(provided))
    issues.extend(_evidence_integrity(output, dsp_report))
    issues.extend(_narrative_x10_scan(output))
    if issues:
        ordered = tuple(
            sorted(issues, key=lambda item: (item.kind.value, item.message))
        )
        return CanonicalValidationResult(
            status=CanonicalValidationStatus.FAILED_CLOSED,
            report=None,
            issues=ordered,
        )
    report = _attach_narratives(dsp_report, output)
    try:
        dumped = report.to_public_dict()
        assert_public_report_privacy(dumped)
    except ValueError:
        return _failed(
            CanonicalValidationKind.PRIVACY,
            "public report failed privacy validation",
        )
    text = str(dumped)
    for canary in _CANARIES:
        if canary in text:
            return _failed(
                CanonicalValidationKind.CANARY,
                "methodology canary leaked into public report",
            )
    return CanonicalValidationResult(
        status=CanonicalValidationStatus.VALID,
        report=report,
        issues=(),
    )


def _require_package(
    research_package: object,
) -> ResearchPackage | CanonicalValidationResult:
    if isinstance(research_package, ResearchPackage):
        if research_package.source_pipeline != SOURCE_PIPELINE_COMPOSE_INTELLIGENCE:
            return _invalid(
                "validate_canonical_research requires source_pipeline="
                f"{SOURCE_PIPELINE_COMPOSE_INTELLIGENCE!r}"
            )
        return research_package
    name = type(research_package).__name__
    return _invalid(
        "validate_canonical_research requires a compose_intelligence "
        f"ResearchPackage, not {name}."
    )


def _parse_ai_output(
    ai_output: object,
) -> tuple[CanonicalAIResearchOutput, Mapping[str, Any]] | CanonicalValidationResult:
    if isinstance(ai_output, CanonicalAIResearchOutput):
        provided = _provided_from_dataclass(ai_output)
        return ai_output, provided
    if not isinstance(ai_output, Mapping):
        return _invalid(
            "AI output must be CanonicalAIResearchOutput or a mapping"
        )
    payload = {str(k): v for k, v in ai_output.items()}
    leaked = contains_private_fields(payload)
    leaked.extend(str(k) for k in payload if str(k) in PRIVATE_REPORT_FIELD_NAMES)
    if leaked:
        return _failed(
            CanonicalValidationKind.PRIVACY,
            "AI output contains private fields: " + ", ".join(sorted(set(leaked))),
        )
    unknown = sorted(set(payload) - ALLOWED_AI_FIELD_NAMES)
    if unknown:
        return _invalid(
            "AI output contains unsupported fields: " + ", ".join(unknown)
        )
    try:
        output = _output_from_mapping(payload)
    except (TypeError, ValueError):
        return _invalid("AI output could not be parsed")
    return output, payload


def _provided_from_dataclass(output: CanonicalAIResearchOutput) -> dict[str, Any]:
    provided: dict[str, Any] = {}
    for item in fields(output):
        value = getattr(output, item.name)
        if item.name == "evidence_ids":
            provided[item.name] = value
            continue
        if value is not None:
            provided[item.name] = value
    return provided


def _output_from_mapping(payload: Mapping[str, Any]) -> CanonicalAIResearchOutput:
    evidence = payload.get("evidence_ids") or ()
    if isinstance(evidence, str):
        evidence = (evidence,)
    evidence_ids = tuple(str(item) for item in evidence)
    iv = payload.get("intrinsic_value")
    if iv is None:
        iv = payload.get("intrinsic_value_per_share")
    return CanonicalAIResearchOutput(
        executive_summary=_as_text(payload.get("executive_summary")),
        valuation_narrative=_as_text(payload.get("valuation_narrative")),
        business_quality_narrative=_as_text(
            payload.get("business_quality_narrative")
        ),
        economic_moat_narrative=_as_text(payload.get("economic_moat_narrative")),
        management_quality_narrative=_as_text(
            payload.get("management_quality_narrative")
        ),
        financial_strength_narrative=_as_text(
            payload.get("financial_strength_narrative")
        ),
        earnings_quality_narrative=_as_text(
            payload.get("earnings_quality_narrative")
        ),
        growth_quality_narrative=_as_text(payload.get("growth_quality_narrative")),
        financials_narrative=_as_text(payload.get("financials_narrative")),
        buffett_narrative=_as_text(payload.get("buffett_narrative")),
        risk_narrative=_as_text(payload.get("risk_narrative")),
        recommendation_narrative=_as_text(payload.get("recommendation_narrative")),
        current_price=_as_number(payload.get("current_price")),
        intrinsic_value=_as_number(iv),
        valuation_range_low=_as_number(payload.get("valuation_range_low")),
        valuation_range_mid=_as_number(payload.get("valuation_range_mid")),
        valuation_range_high=_as_number(payload.get("valuation_range_high")),
        margin_of_safety=_as_number(payload.get("margin_of_safety")),
        financial_metrics=_optional_number_map(payload.get("financial_metrics")),
        quality_scores=_optional_number_map(payload.get("quality_scores")),
        buffett_overall_score_100=_as_number(
            payload.get("buffett_overall_score_100")
        ),
        buffett_methodology=_as_text(payload.get("buffett_methodology")),
        buffett_weights=_as_mapping(payload.get("buffett_weights")),
        circle_of_competence_score=_as_number(
            payload.get("circle_of_competence_score")
        ),
        recommendation_action=_as_text(payload.get("recommendation_action")),
        recommendation_score_100=_as_number(
            payload.get("recommendation_score_100")
        ),
        score_10=payload.get("score_10"),
        score_10_status=_as_text(payload.get("score_10_status")),
        entry_price=_as_number(payload.get("entry_price")),
        buy_price=_as_number(payload.get("buy_price")),
        target_price=_as_number(payload.get("target_price")),
        exit_price=_as_number(payload.get("exit_price")),
        stop_loss=_as_number(payload.get("stop_loss")),
        entry_zone=_as_number(payload.get("entry_zone")),
        scenarios=_as_mapping(payload.get("scenarios")),
        expected_return=_as_number(payload.get("expected_return")),
        expected_returns=_as_number(payload.get("expected_returns")),
        forward_cagr=_as_number(payload.get("forward_cagr")),
        forecast_cagr=_as_number(payload.get("forecast_cagr")),
        evidence_ids=evidence_ids,
    )


def _numerical_integrity(
    output: CanonicalAIResearchOutput,
    provided: Mapping[str, Any],
    report: PublicResearchReport,
) -> list[CanonicalValidationIssue]:
    issues: list[CanonicalValidationIssue] = []
    checks = (
        ("current_price", report.valuation.current_price.value),
        ("intrinsic_value", report.valuation.intrinsic_value_per_share.value),
        (
            "intrinsic_value_per_share",
            report.valuation.intrinsic_value_per_share.value,
        ),
        ("margin_of_safety", report.valuation.margin_of_safety.value),
        ("valuation_range_low", report.valuation.valuation_range.low),
        ("valuation_range_mid", report.valuation.valuation_range.mid),
        ("valuation_range_high", report.valuation.valuation_range.high),
        (
            "buffett_overall_score_100",
            report.buffett_analysis.buffett_overall_score_100,
        ),
        (
            "recommendation_score_100",
            report.recommendation.recommendation_score_100,
        ),
    )
    for key, dsp_value in checks:
        if key not in provided:
            continue
        issue = _compare_provided_number(key, dsp_value, provided.get(key))
        if issue is not None:
            issues.append(issue)
    if "quality_scores" in provided:
        issues.extend(_compare_quality_scores(output.quality_scores, report))
    if "financial_metrics" in provided:
        issues.extend(_compare_financial_metrics(output.financial_metrics, report))
    return issues


def _compare_provided_number(
    field: str, dsp_value: float | None, raw: object
) -> CanonicalValidationIssue | None:
    if raw is None:
        if dsp_value is not None:
            return CanonicalValidationIssue(
                kind=CanonicalValidationKind.MISSING_DATA_FILL,
                message=f"AI set {field} empty while DSP value is present",
            )
        return None
    ai_value = _as_number(raw)
    if ai_value is None:
        return CanonicalValidationIssue(
            kind=CanonicalValidationKind.INVALID_INPUT,
            message=f"AI {field} is not a number",
        )
    if dsp_value is None:
        return CanonicalValidationIssue(
            kind=CanonicalValidationKind.MISSING_DATA_FILL,
            message=f"AI filled unavailable DSP field {field}",
        )
    if not _numbers_equal(dsp_value, ai_value):
        kind = CanonicalValidationKind.NUMERICAL_MISMATCH
        if field == "buffett_overall_score_100":
            kind = CanonicalValidationKind.BUFFETT_MISMATCH
        if field == "recommendation_score_100":
            kind = CanonicalValidationKind.RECOMMENDATION_MISMATCH
        return CanonicalValidationIssue(
            kind=kind,
            message=f"AI {field} does not match ResearchPackage",
        )
    return None


def _compare_quality_scores(
    scores: Mapping[str, float | None] | None,
    report: PublicResearchReport,
) -> list[CanonicalValidationIssue]:
    if not isinstance(scores, Mapping):
        return [
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.INVALID_INPUT,
                message="quality_scores must be a mapping",
            )
        ]
    issues: list[CanonicalValidationIssue] = []
    for attr in _QUALITY_ATTRS:
        if attr not in scores:
            continue
        factor: QualityFactorPublic = getattr(report, attr)
        issue = _compare_provided_number(
            f"quality_scores.{attr}", factor.score_100, scores.get(attr)
        )
        if issue is not None:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.NUMERICAL_MISMATCH,
                    message=issue.message,
                )
            )
    unknown = sorted(set(scores) - set(_QUALITY_ATTRS))
    for name in unknown:
        if scores.get(name) is not None:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.NUMERICAL_MISMATCH,
                    message=f"AI invented quality score {name}",
                )
            )
    return issues


def _compare_financial_metrics(
    metrics: Mapping[str, float | None] | None,
    report: PublicResearchReport,
) -> list[CanonicalValidationIssue]:
    if not isinstance(metrics, Mapping):
        return [
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.INVALID_INPUT,
                message="financial_metrics must be a mapping",
            )
        ]
    dsp = {row.name: row.value for row in report.financials.metrics}
    issues: list[CanonicalValidationIssue] = []
    for name, raw in metrics.items():
        if raw is None:
            continue
        if name not in dsp:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.NUMERICAL_MISMATCH,
                    message=f"AI invented financial metric {name}",
                )
            )
            continue
        issue = _compare_provided_number(
            f"financial_metrics.{name}", dsp[name], raw
        )
        if issue is not None:
            issues.append(issue)
    return issues


def _recommendation_integrity(
    output: CanonicalAIResearchOutput,
    provided: Mapping[str, Any],
    report: PublicResearchReport,
) -> list[CanonicalValidationIssue]:
    if "recommendation_action" not in provided:
        return []
    dsp = _norm_action(report.recommendation.action)
    ai = _norm_action(output.recommendation_action)
    if not dsp:
        return [
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.MISSING_DATA_FILL,
                message="AI filled unavailable DSP recommendation",
            )
        ]
    if ai != dsp:
        return [
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.RECOMMENDATION_MISMATCH,
                message="AI recommendation does not match ResearchPackage",
            )
        ]
    return []


def _buffett_integrity(
    output: CanonicalAIResearchOutput,
    provided: Mapping[str, Any],
    report: PublicResearchReport,
) -> list[CanonicalValidationIssue]:
    issues: list[CanonicalValidationIssue] = []
    if "buffett_methodology" in provided:
        method = (output.buffett_methodology or "").strip()
        if method != BUFFETT_METHODOLOGY:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.BUFFETT_MISMATCH,
                    message="AI attempted to replace Buffett methodology",
                )
            )
    if output.buffett_weights:
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.BUFFETT_MISMATCH,
                message="AI attempted to supply Buffett weights",
            )
        )
    if output.circle_of_competence_score is not None:
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.BUFFETT_MISMATCH,
                message="AI invented a circle-of-competence score",
            )
        )
    if report.buffett_analysis.methodology != BUFFETT_METHODOLOGY:
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.BUFFETT_MISMATCH,
                message="ResearchPackage Buffett methodology is not canonical",
            )
        )
    return issues


def _score_10_integrity(
    output: CanonicalAIResearchOutput,
    provided: Mapping[str, Any],
) -> list[CanonicalValidationIssue]:
    issues: list[CanonicalValidationIssue] = []
    if "score_10" in provided and _has_numeric_score_10(provided.get("score_10")):
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.SCORE_10_FORBIDDEN,
                message="X/10 scoring is not implemented; AI must not supply score_10",
            )
        )
    status = output.score_10_status
    if status is not None and status != SCORE_10_STATUS:
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.SCORE_10_FORBIDDEN,
                message="score_10_status must remain not_implemented",
            )
        )
    return issues


def _has_numeric_score_10(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, Mapping):
        return any(_as_number(item) is not None for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_as_number(item) is not None for item in value)
    return False


def _entry_exit_integrity(
    provided: Mapping[str, Any],
) -> list[CanonicalValidationIssue]:
    issues: list[CanonicalValidationIssue] = []
    for name in _ENTRY_EXIT_FIELDS:
        if name not in provided:
            continue
        if _as_number(provided.get(name)) is not None:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.ENTRY_EXIT_FORBIDDEN,
                    message=f"AI invented {name}; entry/exit is not_implemented",
                )
            )
    return issues


def _scenario_integrity(
    provided: Mapping[str, Any],
) -> list[CanonicalValidationIssue]:
    if "scenarios" not in provided:
        return []
    raw = provided.get("scenarios")
    if raw is None:
        return []
    if not isinstance(raw, Mapping):
        return [
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.SCENARIO_FORBIDDEN,
                message="AI invented scenarios; canonical path has none",
            )
        ]
    issues: list[CanonicalValidationIssue] = []
    for name in ("bear", "base", "bull"):
        if _scenario_has_value(raw.get(name)):
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.SCENARIO_FORBIDDEN,
                    message=f"AI invented {name} scenario value",
                )
            )
    extra = sorted(set(raw) - {"bear", "base", "bull"})
    if extra:
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.SCENARIO_FORBIDDEN,
                message="AI invented unsupported scenario keys",
            )
        )
    return issues


def _scenario_has_value(item: object) -> bool:
    if item is None:
        return False
    if isinstance(item, bool):
        return False
    if isinstance(item, (int, float)):
        return True
    if isinstance(item, Mapping):
        if _as_number(item.get("value")) is not None:
            return True
        status = str(item.get("status") or "").strip().lower()
        return status not in {"", "unavailable", "not_implemented"}
    return bool(item)


def _expected_return_integrity(
    provided: Mapping[str, Any],
) -> list[CanonicalValidationIssue]:
    issues: list[CanonicalValidationIssue] = []
    for name in _EXPECTED_RETURN_FIELDS:
        if name not in provided:
            continue
        if _as_number(provided.get(name)) is not None:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.EXPECTED_RETURN_FORBIDDEN,
                    message=(
                        f"AI invented {name}; expected return is not_implemented"
                    ),
                )
            )
    return issues


def _evidence_integrity(
    output: CanonicalAIResearchOutput,
    report: PublicResearchReport,
) -> list[CanonicalValidationIssue]:
    allowed = {item.id for item in report.evidence}
    issues: list[CanonicalValidationIssue] = []
    for evidence_id in output.evidence_ids:
        if evidence_id not in allowed:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.INVALID_EVIDENCE,
                    message=f"evidence id is not in ResearchPackage: {evidence_id}",
                )
            )
    needs_evidence = any(
        _as_text(getattr(output, name)) for name in _MATERIAL_NARRATIVES
    )
    if needs_evidence and not output.evidence_ids:
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.MISSING_EVIDENCE,
                message="material AI narrative is missing evidence references",
            )
        )
    return issues


def _narrative_x10_scan(
    output: CanonicalAIResearchOutput,
) -> list[CanonicalValidationIssue]:
    blob = " ".join(
        text
        for name in _NARRATIVE_FIELDS
        for text in (_as_text(getattr(output, name)),)
        if text
    )
    if _X10_IN_TEXT.search(blob):
        return [
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.SCORE_10_FORBIDDEN,
                message="AI narrative manufactured an X/10 score",
            )
        ]
    return []


def _privacy_and_canary(
    output: CanonicalAIResearchOutput,
    provided: Mapping[str, Any],
) -> list[CanonicalValidationIssue]:
    issues: list[CanonicalValidationIssue] = []
    leaked = contains_private_fields(dict(provided))
    if leaked:
        issues.append(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.PRIVACY,
                message="AI output contains private fields: "
                + ", ".join(sorted(set(leaked))),
            )
        )
    blob = " ".join(
        [
            *(
                text
                for name in _NARRATIVE_FIELDS
                for text in (_as_text(getattr(output, name)),)
                if text
            ),
            *(str(v) for v in provided.values() if isinstance(v, str)),
        ]
    )
    for canary in _CANARIES:
        if canary in blob:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.CANARY,
                    message="private methodology canary echoed in AI output",
                )
            )
            break
    lowered = blob.lower()
    for token in _PRIVACY_TEXT_TOKENS:
        if token in lowered:
            issues.append(
                CanonicalValidationIssue(
                    kind=CanonicalValidationKind.PRIVACY,
                    message=f"private field echoed in AI output: {token}",
                )
            )
    return issues


def _attach_narratives(
    report: PublicResearchReport,
    output: CanonicalAIResearchOutput,
) -> PublicResearchReport:
    return replace(
        report,
        executive_summary=_ai_narrative(output.executive_summary),
        business_quality=_with_narrative(
            report.business_quality, output.business_quality_narrative
        ),
        economic_moat=_with_narrative(
            report.economic_moat, output.economic_moat_narrative
        ),
        management_quality=_with_narrative(
            report.management_quality, output.management_quality_narrative
        ),
        financial_strength=_with_narrative(
            report.financial_strength, output.financial_strength_narrative
        ),
        earnings_quality=_with_narrative(
            report.earnings_quality, output.earnings_quality_narrative
        ),
        growth_quality=_with_narrative(
            report.growth_quality, output.growth_quality_narrative
        ),
        buffett_analysis=replace(
            report.buffett_analysis,
            narrative=_ai_narrative(output.buffett_narrative),
        ),
        financials=replace(
            report.financials,
            narrative=_ai_narrative(output.financials_narrative),
        ),
        valuation=replace(
            report.valuation,
            narrative=_ai_narrative(output.valuation_narrative),
        ),
        recommendation=replace(
            report.recommendation,
            narrative=_ai_narrative(output.recommendation_narrative),
        ),
        risk=replace(
            report.risk,
            narrative=_ai_narrative(output.risk_narrative),
        ),
    )


def _with_narrative(
    factor: QualityFactorPublic, text: str | None
) -> QualityFactorPublic:
    return replace(factor, narrative=_ai_narrative(text))


def _ai_narrative(text: str | None) -> AiNarrative:
    cleaned = _as_text(text)
    if cleaned is None:
        return empty_ai_narrative()
    return AiNarrative(text=cleaned, status="available", source="ai")


def _numbers_equal(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=_ABS_TOL)


def _norm_action(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip().upper()


def _as_text(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _as_number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Mapping):
        return _as_number(value.get("value"))
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_mapping(value: object) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return {str(k): value[k] for k in value}
    return None


def _optional_number_map(
    value: object,
) -> dict[str, float | None] | None:
    mapping = _as_mapping(value)
    if mapping is None:
        return None
    return {key: _as_number(item) for key, item in mapping.items()}


def _invalid(message: str) -> CanonicalValidationResult:
    return CanonicalValidationResult(
        status=CanonicalValidationStatus.INVALID,
        report=None,
        issues=(
            CanonicalValidationIssue(
                kind=CanonicalValidationKind.INVALID_INPUT,
                message=message,
            ),
        ),
    )


def _failed(
    kind: CanonicalValidationKind, message: str
) -> CanonicalValidationResult:
    return CanonicalValidationResult(
        status=CanonicalValidationStatus.FAILED_CLOSED,
        report=None,
        issues=(CanonicalValidationIssue(kind=kind, message=message),),
    )
