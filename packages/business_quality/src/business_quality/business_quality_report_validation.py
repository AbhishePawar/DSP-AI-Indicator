"""Validation for Business Quality report aggregation (F3.7)."""

from __future__ import annotations

from typing import Any

from business_quality.exceptions import BusinessQualityValidationError
from business_quality.validation import BusinessQualityValidation

__all__ = [
    "BusinessQualityReportValidationError",
    "validate_business_quality_analysis",
    "validate_report_metadata",
    "validate_report_object",
]

BusinessQualityReportValidationError = BusinessQualityValidationError


def validate_business_quality_analysis(source: Any) -> BusinessQualityValidation:
    """Accept ONLY ``BusinessQualityAnalysis``; reject missing inputs."""
    if source is None:
        raise BusinessQualityValidationError("Missing BusinessQualityAnalysis")

    type_name = type(source).__name__
    if type_name != "BusinessQualityAnalysis":
        raise BusinessQualityValidationError(
            f"Accept ONLY BusinessQualityAnalysis, got {type_name}"
        )

    required_attrs = (
        "metadata",
        "validation",
        "summary",
        "quality_flags",
        "explainability",
        "research_disclaimer",
        "overall_confidence",
    )
    missing = [a for a in required_attrs if not hasattr(source, a)]
    if missing:
        raise BusinessQualityValidationError(
            "Missing BusinessQualityAnalysis: object lacks " + ", ".join(missing)
        )

    meta_result = validate_report_metadata(getattr(source, "metadata", None))
    warnings: list[str] = list(meta_result.warnings)
    if getattr(source, "overall_score", None) is None:
        warnings.append("overall_score unavailable")
    if getattr(source, "overall_rating", None) is None:
        warnings.append("overall_rating unavailable")

    return BusinessQualityValidation(
        ok=True,
        required_inputs=required_attrs,
        missing_inputs=(),
        invalid_inputs=(),
        checks=tuple(meta_result.checks) + ("business_quality_analysis_ok=True",),
        warnings=tuple(dict.fromkeys(warnings)),
        errors=(),
    )


def validate_report_metadata(metadata: Any) -> BusinessQualityValidation:
    """Reject invalid report metadata."""
    if metadata is None:
        raise BusinessQualityValidationError("Invalid metadata: missing metadata")

    engine_version = getattr(metadata, "engine_version", None)
    if not engine_version:
        raise BusinessQualityValidationError(
            "Invalid metadata: engine_version is required"
        )

    schema = getattr(metadata, "schema_version", None)
    warnings: list[str] = []
    if schema is None or str(schema) == "":
        warnings.append("schema_version missing")

    return BusinessQualityValidation(
        ok=True,
        required_inputs=("engine_version",),
        missing_inputs=(),
        invalid_inputs=(),
        checks=(f"engine_version={engine_version}",),
        warnings=tuple(warnings),
        errors=(),
    )


def validate_report_object(report: Any) -> BusinessQualityValidation:
    """Reject invalid report objects after aggregation."""
    if report is None:
        raise BusinessQualityValidationError("Invalid report objects: report is None")

    type_name = type(report).__name__
    if type_name != "BusinessQualityReport":
        raise BusinessQualityValidationError(
            f"Invalid report objects: expected BusinessQualityReport, got {type_name}"
        )

    required = (
        "metadata",
        "validation",
        "executive_summary",
        "confidence_summary",
        "module_breakdown",
        "explainability",
        "research_disclaimer",
    )
    missing = [a for a in required if not hasattr(report, a)]
    if missing:
        raise BusinessQualityValidationError(
            "Invalid report objects: missing " + ", ".join(missing)
        )

    validate_report_metadata(report.metadata)
    if not isinstance(getattr(report, "executive_summary", None), str):
        raise BusinessQualityValidationError(
            "Invalid report objects: executive_summary must be a string"
        )
    if not isinstance(getattr(report, "module_breakdown", None), tuple):
        raise BusinessQualityValidationError(
            "Invalid report objects: module_breakdown must be a tuple"
        )

    return BusinessQualityValidation(
        ok=True,
        required_inputs=required,
        missing_inputs=(),
        invalid_inputs=(),
        checks=("report_object_ok=True",),
        warnings=(),
        errors=(),
    )
