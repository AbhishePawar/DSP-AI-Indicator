"""Citation / reference types — Research never embeds upstream payloads."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

__all__ = [
    "ComparisonReference",
    "DecisionReference",
    "EvidenceReference",
    "IntegratedRiskReference",
    "MonitoringReference",
    "PortfolioReference",
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


@dataclass(frozen=True, slots=True)
class DecisionReference:
    """Citation of a DecisionPack — never embeds the pack payload."""

    instrument_symbol: str
    digest: str

    def __post_init__(self) -> None:
        symbol = self.instrument_symbol.strip().upper()
        if not symbol:
            msg = "broken references: DecisionPack symbol invalid"
            raise ValidationError(msg)
        digest = _normalize_digest(self.digest, field="decision")
        object.__setattr__(self, "instrument_symbol", symbol)
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    """Citation of an EvidenceBundle — never embeds evidence payload."""

    bundle_id: str
    digest: str
    instrument_key: str | None = None

    def __post_init__(self) -> None:
        bundle_id = _normalize_id(self.bundle_id, field="bundle_id")
        digest = _normalize_digest(self.digest, field="evidence")
        instrument_key = (
            None
            if self.instrument_key is None
            else self.instrument_key.strip().upper() or None
        )
        object.__setattr__(self, "bundle_id", bundle_id)
        object.__setattr__(self, "digest", digest)
        object.__setattr__(self, "instrument_key", instrument_key)


@dataclass(frozen=True, slots=True)
class ComparisonReference:
    """Citation of a ComparisonReport — never embeds comparison payload."""

    digest: str
    report_id: str | None = None

    def __post_init__(self) -> None:
        digest = _normalize_digest(self.digest, field="comparison")
        report_id = (
            None
            if self.report_id is None
            else _normalize_id(self.report_id, field="report_id")
        )
        object.__setattr__(self, "digest", digest)
        object.__setattr__(self, "report_id", report_id)


@dataclass(frozen=True, slots=True)
class PortfolioReference:
    """Citation of a Portfolio — never embeds the Portfolio payload."""

    portfolio_id: str
    snapshot_id: str | None = None

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        snapshot_id = (
            None
            if self.snapshot_id is None
            else _normalize_id(self.snapshot_id, field="snapshot_id")
        )
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "snapshot_id", snapshot_id)


@dataclass(frozen=True, slots=True)
class MonitoringReference:
    """Citation of Portfolio Monitoring state — never embeds monitoring payloads."""

    portfolio_id: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        portfolio_id = _normalize_id(self.portfolio_id, field="portfolio_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "portfolio_id", portfolio_id)
        object.__setattr__(self, "notes", notes)


@dataclass(frozen=True, slots=True)
class RiskReference:
    """Citation of a RiskReport / RiskProfile — never embeds risk payloads."""

    risk_id: str
    assessment_id: str | None = None
    report_digest: str | None = None

    def __post_init__(self) -> None:
        risk_id = _normalize_id(self.risk_id, field="risk_id")
        assessment_id = (
            None
            if self.assessment_id is None
            else _normalize_id(self.assessment_id, field="assessment_id")
        )
        report_digest = (
            None
            if self.report_digest is None
            else _normalize_digest(self.report_digest, field="risk_report")
        )
        object.__setattr__(self, "risk_id", risk_id)
        object.__setattr__(self, "assessment_id", assessment_id)
        object.__setattr__(self, "report_digest", report_digest)


@dataclass(frozen=True, slots=True)
class IntegratedRiskReference:
    """Citation of an IntegratedRiskContext — never embeds the context payload."""

    risk_id: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        risk_id = _normalize_id(self.risk_id, field="risk_id")
        notes = tuple(n.strip() for n in self.notes if n.strip())
        object.__setattr__(self, "risk_id", risk_id)
        object.__setattr__(self, "notes", notes)
