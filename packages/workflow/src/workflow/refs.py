"""Citation / reference types — Workflow never embeds upstream payloads."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

__all__ = [
    "AnalysisReference",
    "ComparisonReference",
    "DecisionReference",
    "IndustryEvidenceReference",
    "PortfolioReference",
    "QuantitativeRiskReference",
    "RecommendationReference",
    "ResearchReference",
    "RiskReference",
    "_normalize_id",
]


def _normalize_id(value: str, *, field: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    if any(ch.isspace() for ch in cleaned):
        msg = f"{field} must not contain whitespace"
        raise ValidationError(msg)
    return cleaned


def _normalize_digest(value: str, *, field: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned or len(cleaned) < 8:
        msg = f"broken references: {field} digest invalid"
        raise ValidationError(msg)
    if any(ch.isspace() for ch in cleaned):
        msg = f"{field} must not contain whitespace"
        raise ValidationError(msg)
    return cleaned


def _non_empty(text: str, *, field: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        msg = f"{field} must not be empty"
        raise ValidationError(msg)
    return cleaned


@dataclass(frozen=True, slots=True)
class _OutcomeReferenceBase:
    """Shared citation fields for upstream execution outcomes."""

    id: str
    report_id: str
    version: str
    digest: str
    status: str
    generated_at: str

    def _normalize(self) -> tuple[str, str, str, str, str, str]:
        return (
            _normalize_id(self.id, field="id"),
            _normalize_id(self.report_id, field="report_id"),
            _non_empty(self.version, field="version"),
            _normalize_digest(self.digest, field="digest"),
            _non_empty(self.status, field="status").lower().replace(" ", "_"),
            _non_empty(self.generated_at, field="generated_at"),
        )


@dataclass(frozen=True, slots=True)
class AnalysisReference(_OutcomeReferenceBase):
    """Citation of an Analysis Framework run outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class DecisionReference(_OutcomeReferenceBase):
    """Citation of a DecisionPack outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class IndustryEvidenceReference(_OutcomeReferenceBase):
    """Citation of an EvidenceBundle outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class ComparisonReference(_OutcomeReferenceBase):
    """Citation of a ComparisonReport outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class PortfolioReference(_OutcomeReferenceBase):
    """Citation of a Portfolio / monitoring outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class RiskReference(_OutcomeReferenceBase):
    """Citation of a qualitative RiskReport outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class ResearchReference(_OutcomeReferenceBase):
    """Citation of a ResearchReport outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class QuantitativeRiskReference(_OutcomeReferenceBase):
    """Citation of a QuantitativeRiskReport outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class RecommendationReference(_OutcomeReferenceBase):
    """Citation of a RecommendationReport outcome."""

    def __post_init__(self) -> None:
        values = self._normalize()
        for name, value in zip(
            ("id", "report_id", "version", "digest", "status", "generated_at"),
            values,
            strict=True,
        ):
            object.__setattr__(self, name, value)
