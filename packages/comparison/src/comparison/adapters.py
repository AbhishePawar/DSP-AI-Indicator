"""Public JSON-friendly projection of comparison outputs.

Mirrors ``dsp_platform.composition.adapters.pipeline_result_public_dict`` —
a pure structural mapping from frozen comparison dataclasses to plain
dicts/lists/strings for HTTP transport. No comparison logic lives here.
"""

from __future__ import annotations

from typing import Any

from comparison.models import (
    ComparisonDimensionResult,
    ComparisonEvidenceSummary,
    ComparisonExplanation,
    ComparisonLimitation,
    ComparisonObservation,
    ComparisonReport,
    ComparisonResult,
)

__all__ = ["comparison_result_public_dict"]


def _observation_dict(observation: ComparisonObservation) -> dict[str, Any]:
    return {
        "code": observation.code,
        "text": observation.text,
        "dimension": _enum_value(observation.dimension),
        "subjects": list(observation.subjects),
        "evidence_refs": list(observation.evidence_refs),
    }


def _limitation_dict(limitation: ComparisonLimitation) -> dict[str, Any]:
    return {
        "code": limitation.code,
        "message": limitation.message,
        "subjects": list(limitation.subjects),
    }


def _dimension_result_dict(result: ComparisonDimensionResult) -> dict[str, Any]:
    return {
        "dimension": _enum_value(result.dimension),
        "observations": [_observation_dict(o) for o in result.observations],
    }


def _explanation_dict(explanation: ComparisonExplanation) -> dict[str, Any]:
    return {"summary": explanation.summary, "detail": explanation.detail}


def _evidence_summary_dict(
    summary: ComparisonEvidenceSummary | None,
) -> dict[str, Any] | None:
    if summary is None:
        return None
    return {
        "attached": summary.attached,
        "availability": summary.availability,
        "bundle_count": summary.bundle_count,
        "covered_symbols": list(summary.covered_symbols),
        "missing_symbols": list(summary.missing_symbols),
        "methodology_id": summary.methodology_id,
        "bundle_versions": list(summary.bundle_versions),
        "bundle_statuses": list(summary.bundle_statuses),
        "digests": list(summary.digests),
    }


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _report_dict(report: ComparisonReport) -> dict[str, Any]:
    return {
        "status": _enum_value(report.status),
        "scope_notes": list(report.scope_notes),
        "methodology_id": report.methodology_id,
        "methodology_version": report.methodology_version,
        "industry_id": report.industry_id,
        "included_symbols": list(report.included_symbols),
        "excluded_symbols": list(report.excluded_symbols),
        "exclusion_reasons": list(report.exclusion_reasons),
        "eligibility_group_status": _enum_value(report.eligibility_group_status),
        "dimension_results": [
            _dimension_result_dict(d) for d in report.dimension_results
        ],
        "shared_observations": [
            _observation_dict(o) for o in report.shared_observations
        ],
        "pair_observations": [_observation_dict(o) for o in report.pair_observations],
        "decision_context": [_observation_dict(o) for o in report.decision_context],
        "valuation_context": [_observation_dict(o) for o in report.valuation_context],
        "robustness_context": [
            _observation_dict(o) for o in report.robustness_context
        ],
        "limitations": [_limitation_dict(lim) for lim in report.limitations],
        "research_priorities": list(report.research_priorities),
        "explanation": _explanation_dict(report.explanation),
        "evidence_summary": _evidence_summary_dict(report.evidence_summary),
        "evidence_observations": [
            _observation_dict(o) for o in report.evidence_observations
        ],
        "evidence_limitations": [
            _limitation_dict(lim) for lim in report.evidence_limitations
        ],
    }


def comparison_result_public_dict(result: ComparisonResult) -> dict[str, Any]:
    """Project a ``ComparisonResult`` into a JSON-friendly dict for the API layer."""
    return {
        "status": _enum_value(result.status),
        "refused": result.refused,
        "report": _report_dict(result.report),
    }
