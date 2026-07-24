"""Decision Brief domain models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from contracts.domain.evidence import Evidence
from contracts.domain.instrument import Instrument
from contracts.enums import RecommendationAction
from core.exceptions import ValidationError

__all__ = [
    "DecisionBrief",
    "EvidenceHighlight",
    "MemberAttribution",
]


@dataclass(frozen=True, slots=True)
class MemberAttribution:
    """How one committee member relates to the final recommendation."""

    source: str
    stance: str
    agreed_with_final: bool
    role: str
    rationale_excerpt: str

    def __post_init__(self) -> None:
        source = self.source.strip().lower()
        stance = self.stance.strip().lower()
        role = self.role.strip().lower()
        excerpt = self.rationale_excerpt.strip()
        if not source:
            msg = "source must not be empty"
            raise ValidationError(msg)
        if not stance:
            msg = "stance must not be empty"
            raise ValidationError(msg)
        if role not in {"supporting", "dissenting", "neutral"}:
            msg = f"role must be supporting, dissenting, or neutral; got {role!r}"
            raise ValidationError(msg)
        if not excerpt:
            msg = "rationale_excerpt must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "stance", stance)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "rationale_excerpt", excerpt)


@dataclass(frozen=True, slots=True)
class EvidenceHighlight:
    """Strongest or weakest evidence item with a short reason."""

    claim: str
    source_engine: str
    strength: str
    rank_reason: str
    value: float | None = None

    def __post_init__(self) -> None:
        claim = self.claim.strip()
        strength = self.strength.strip().lower()
        reason = self.rank_reason.strip()
        engine = self.source_engine.strip().lower()
        if not claim:
            msg = "claim must not be empty"
            raise ValidationError(msg)
        if strength not in {"strong", "weak"}:
            msg = f"strength must be strong or weak; got {strength!r}"
            raise ValidationError(msg)
        if not reason:
            msg = "rank_reason must not be empty"
            raise ValidationError(msg)
        if not engine:
            msg = "source_engine must not be empty"
            raise ValidationError(msg)
        object.__setattr__(self, "claim", claim)
        object.__setattr__(self, "strength", strength)
        object.__setattr__(self, "rank_reason", reason)
        object.__setattr__(self, "source_engine", engine)

    @classmethod
    def from_evidence(
        cls,
        evidence: Evidence,
        *,
        strength: str,
        rank_reason: str,
    ) -> EvidenceHighlight:
        return cls(
            claim=evidence.claim,
            source_engine=evidence.source_engine.value,
            strength=strength,
            rank_reason=rank_reason,
            value=evidence.value,
        )


@dataclass(frozen=True, slots=True)
class DecisionBrief:
    """Investor-facing explanation of an already completed recommendation."""

    instrument: Instrument
    action: RecommendationAction
    conviction: float
    headline: str
    executive_summary: str
    attribution: tuple[MemberAttribution, ...]
    evidence_highlights: tuple[EvidenceHighlight, ...]
    key_assumptions: tuple[str, ...]
    invalidators: tuple[str, ...]
    monitoring_watchlist: tuple[str, ...]
    generated_at: datetime

    def __post_init__(self) -> None:
        headline = self.headline.strip()
        summary = self.executive_summary.strip()
        if not headline:
            msg = "headline must not be empty"
            raise ValidationError(msg)
        if not summary:
            msg = "executive_summary must not be empty"
            raise ValidationError(msg)
        if not (0.0 <= self.conviction <= 1.0):
            msg = "conviction must be in [0.0, 1.0]"
            raise ValidationError(msg)
        object.__setattr__(self, "headline", headline)
        object.__setattr__(self, "executive_summary", summary)
        object.__setattr__(self, "attribution", tuple(self.attribution))
        object.__setattr__(
            self, "evidence_highlights", tuple(self.evidence_highlights)
        )
        object.__setattr__(self, "key_assumptions", tuple(self.key_assumptions))
        object.__setattr__(self, "invalidators", tuple(self.invalidators))
        object.__setattr__(
            self, "monitoring_watchlist", tuple(self.monitoring_watchlist)
        )
