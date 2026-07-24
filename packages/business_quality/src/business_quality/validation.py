"""Reusable validation framework for Business Quality inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from business_quality.exceptions import BusinessQualityValidationError
from business_quality.scoring import Confidence, EvidenceLevel

__all__ = [
    "BusinessQualityValidation",
    "validate_required_inputs",
    "validate_confidence",
    "validate_evidence_level",
    "empty_validation",
]


@dataclass(frozen=True, slots=True)
class BusinessQualityValidation:
    """Validation summary for a Business Quality analysis artifact."""

    ok: bool
    required_inputs: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()
    invalid_inputs: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "required_inputs": list(self.required_inputs),
            "missing_inputs": list(self.missing_inputs),
            "invalid_inputs": list(self.invalid_inputs),
            "checks": list(self.checks),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def empty_validation(*, ok: bool = True) -> BusinessQualityValidation:
    """Return an empty successful (or failed) validation shell."""
    return BusinessQualityValidation(ok=ok)


def validate_required_inputs(
    payload: Mapping[str, Any] | None,
    required: Sequence[str],
    *,
    raise_on_missing: bool = True,
) -> BusinessQualityValidation:
    """Check that required keys are present and non-``None``.

    Framework-only — does not interpret business meaning of fields.
    """
    required_t = tuple(required)
    if payload is None:
        missing = required_t
        invalid: tuple[str, ...] = ()
    else:
        missing = tuple(k for k in required_t if k not in payload or payload[k] is None)
        invalid = tuple(
            k
            for k, v in payload.items()
            if k in required_t and _is_invalid_scalar(v)
        )

    errors: list[str] = []
    if missing:
        errors.append(f"Missing inputs: {', '.join(missing)}")
    if invalid:
        errors.append(f"Invalid inputs: {', '.join(invalid)}")

    ok = not missing and not invalid
    result = BusinessQualityValidation(
        ok=ok,
        required_inputs=required_t,
        missing_inputs=missing,
        invalid_inputs=invalid,
        checks=(f"required_count={len(required_t)}",),
        warnings=(),
        errors=tuple(errors),
    )
    if raise_on_missing and not ok:
        raise BusinessQualityValidationError("; ".join(errors) or "Validation failed")
    return result


def validate_confidence(
    confidence: Confidence | str | None,
    *,
    allow_insufficient: bool = True,
) -> Confidence:
    """Normalize / validate a confidence value."""
    if confidence is None:
        raise BusinessQualityValidationError("Confidence is required")
    try:
        conf = (
            confidence
            if isinstance(confidence, Confidence)
            else Confidence(str(confidence))
        )
    except ValueError as exc:
        raise BusinessQualityValidationError(
            f"Invalid confidence: {confidence!r}"
        ) from exc
    if conf is Confidence.INSUFFICIENT and not allow_insufficient:
        raise BusinessQualityValidationError(
            "Insufficient confidence is not allowed for this context"
        )
    return conf


def validate_evidence_level(
    level: EvidenceLevel | str | None,
    *,
    allow_none: bool = True,
) -> EvidenceLevel:
    """Normalize / validate an evidence level."""
    if level is None:
        raise BusinessQualityValidationError("Evidence level is required")
    try:
        ev = (
            level if isinstance(level, EvidenceLevel) else EvidenceLevel(str(level))
        )
    except ValueError as exc:
        raise BusinessQualityValidationError(
            f"Invalid evidence level: {level!r}"
        ) from exc
    if ev is EvidenceLevel.NONE and not allow_none:
        raise BusinessQualityValidationError(
            "Evidence level 'none' is not allowed for this context"
        )
    return ev


def _is_invalid_scalar(value: Any) -> bool:
    if isinstance(value, float):
        return value != value or value in (float("inf"), float("-inf"))
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def merge_validation_results(
    results: Iterable[BusinessQualityValidation],
) -> BusinessQualityValidation:
    """Combine multiple validation results (all must be ok for overall ok)."""
    results_l = list(results)
    if not results_l:
        return empty_validation(ok=True)
    return BusinessQualityValidation(
        ok=all(r.ok for r in results_l),
        required_inputs=tuple(
            dict.fromkeys(x for r in results_l for x in r.required_inputs)
        ),
        missing_inputs=tuple(
            dict.fromkeys(x for r in results_l for x in r.missing_inputs)
        ),
        invalid_inputs=tuple(
            dict.fromkeys(x for r in results_l for x in r.invalid_inputs)
        ),
        checks=tuple(dict.fromkeys(x for r in results_l for x in r.checks)),
        warnings=tuple(dict.fromkeys(x for r in results_l for x in r.warnings)),
        errors=tuple(dict.fromkeys(x for r in results_l for x in r.errors)),
    )
