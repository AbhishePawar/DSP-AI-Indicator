"""Citation / reference types — Recommendation never embeds upstream payloads."""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

__all__ = [
    "ComparisonReference",
    "DecisionReference",
    "PortfolioReference",
    "QuantitativeRiskReference",
    "ResearchReference",
    "RiskReference",
    "_normalize_id",
    "citation_key",
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


def citation_key(kind: str, identifier: str) -> str:
    """Stable opaque citation key for option supporting_report_refs."""
    return f"{kind}:{_normalize_id(identifier, field='citation')}"


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

    @property
    def citation(self) -> str:
        return citation_key("decision", self.digest)


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

    @property
    def citation(self) -> str:
        return citation_key("comparison", self.digest)


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

    @property
    def citation(self) -> str:
        return citation_key("portfolio", self.portfolio_id)


@dataclass(frozen=True, slots=True)
class RiskReference:
    """Citation of a qualitative RiskReport — never embeds risk payloads."""

    risk_id: str
    digest: str | None = None

    def __post_init__(self) -> None:
        risk_id = _normalize_id(self.risk_id, field="risk_id")
        digest = (
            None
            if self.digest is None
            else _normalize_digest(self.digest, field="risk")
        )
        object.__setattr__(self, "risk_id", risk_id)
        object.__setattr__(self, "digest", digest)

    @property
    def citation(self) -> str:
        return citation_key("risk", self.risk_id)


@dataclass(frozen=True, slots=True)
class ResearchReference:
    """Citation of a ResearchReport — never embeds research payloads."""

    research_id: str
    digest: str | None = None

    def __post_init__(self) -> None:
        research_id = _normalize_id(self.research_id, field="research_id")
        digest = (
            None
            if self.digest is None
            else _normalize_digest(self.digest, field="research")
        )
        object.__setattr__(self, "research_id", research_id)
        object.__setattr__(self, "digest", digest)

    @property
    def citation(self) -> str:
        return citation_key("research", self.research_id)


@dataclass(frozen=True, slots=True)
class QuantitativeRiskReference:
    """Citation of a QuantitativeRiskReport — never embeds quant payloads."""

    quantitative_risk_id: str
    digest: str | None = None

    def __post_init__(self) -> None:
        quantitative_risk_id = _normalize_id(
            self.quantitative_risk_id, field="quantitative_risk_id"
        )
        digest = (
            None
            if self.digest is None
            else _normalize_digest(self.digest, field="quantitative_risk")
        )
        object.__setattr__(self, "quantitative_risk_id", quantitative_risk_id)
        object.__setattr__(self, "digest", digest)

    @property
    def citation(self) -> str:
        return citation_key("quantitative_risk", self.quantitative_risk_id)
