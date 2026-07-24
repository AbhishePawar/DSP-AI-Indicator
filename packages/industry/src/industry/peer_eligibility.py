"""Peer eligibility domain models — structural comparison gate only.

Does not compare, score, or rank companies.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.exceptions import ValidationError

from industry.enums import GroupEligibilityStatus, PeerEligibilityStatus
from industry.models import _normalize_id
from industry.semver import require_semver

__all__ = [
    "EligibilityOptions",
    "GroupEligibilityResult",
    "InstrumentIndustryAssignment",
    "InstrumentMethodologyResolution",
    "PeerEligibilityPolicy",
    "PeerEligibilityReason",
    "PeerEligibilityResult",
]

# Higher = more restrictive when combining bidirectional evaluations.
_STATUS_STRICTNESS: dict[PeerEligibilityStatus, int] = {
    PeerEligibilityStatus.DIRECT_PEER: 0,
    PeerEligibilityStatus.RELATED_PEER: 1,
    PeerEligibilityStatus.LIMITED_COMPARISON: 2,
    PeerEligibilityStatus.UNKNOWN: 3,
    PeerEligibilityStatus.INSUFFICIENT_DATA: 4,
    PeerEligibilityStatus.NOT_COMPARABLE: 5,
}


@dataclass(frozen=True, slots=True)
class PeerEligibilityReason:
    """Human- and machine-readable explanation for an eligibility outcome."""

    code: str
    message: str
    details: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        code = self.code.strip().lower().replace(" ", "_")
        if not code:
            msg = "reason code must not be empty"
            raise ValidationError(msg)
        message = self.message.strip()
        if not message:
            msg = "reason message must not be empty"
            raise ValidationError(msg)
        details = tuple(d.strip() for d in self.details if d.strip())
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "details", details)


@dataclass(frozen=True, slots=True)
class PeerEligibilityPolicy:
    """Deterministic structural rules for peer eligibility.

    Inspects industry / business-model identity only — never financial metrics.
    """

    id: str
    version: str
    subject_industry_id: str
    same_industry_status: PeerEligibilityStatus = PeerEligibilityStatus.DIRECT_PEER
    related_industry_ids: tuple[str, ...] = ()
    limited_industry_ids: tuple[str, ...] = ()
    not_comparable_industry_ids: tuple[str, ...] = ()
    default_status: PeerEligibilityStatus = PeerEligibilityStatus.NOT_COMPARABLE
    require_same_business_model_for_direct: bool = False
    related_business_model_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        policy_id = _normalize_id(self.id, field="id")
        version = require_semver(self.version, field="version")
        subject = _normalize_id(self.subject_industry_id, field="subject_industry_id")
        related = _unique_ids(self.related_industry_ids, field="related_industry_ids")
        limited = _unique_ids(self.limited_industry_ids, field="limited_industry_ids")
        refused = _unique_ids(
            self.not_comparable_industry_ids, field="not_comparable_industry_ids"
        )
        related_bm = _unique_ids(
            self.related_business_model_ids, field="related_business_model_ids"
        )
        notes = tuple(n.strip() for n in self.notes if n.strip())

        overlaps = (set(related) & set(limited)) | (set(related) & set(refused)) | (
            set(limited) & set(refused)
        )
        if overlaps:
            msg = (
                f"peer policy {policy_id!r} has industries in multiple buckets: "
                f"{sorted(overlaps)}"
            )
            raise ValidationError(msg)
        if subject in refused:
            msg = (
                f"peer policy {policy_id!r} cannot list subject industry "
                f"as not_comparable"
            )
            raise ValidationError(msg)

        object.__setattr__(self, "id", policy_id)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "subject_industry_id", subject)
        object.__setattr__(self, "related_industry_ids", related)
        object.__setattr__(self, "limited_industry_ids", limited)
        object.__setattr__(self, "not_comparable_industry_ids", refused)
        object.__setattr__(self, "related_business_model_ids", related_bm)
        object.__setattr__(self, "notes", notes)

    @property
    def registry_key(self) -> tuple[str, str]:
        return (self.id, self.version)

    def evaluate_candidate(
        self,
        *,
        candidate_industry_id: str,
        subject_business_model_id: str | None = None,
        candidate_business_model_id: str | None = None,
    ) -> tuple[PeerEligibilityStatus, PeerEligibilityReason]:
        """Evaluate one candidate industry against this subject policy."""
        candidate = candidate_industry_id.strip().lower()
        if not candidate:
            return (
                PeerEligibilityStatus.INSUFFICIENT_DATA,
                PeerEligibilityReason(
                    code="missing_candidate_industry",
                    message="Candidate industry identity is missing.",
                ),
            )

        if candidate in self.not_comparable_industry_ids:
            return (
                PeerEligibilityStatus.NOT_COMPARABLE,
                PeerEligibilityReason(
                    code="explicit_not_comparable",
                    message=(
                        f"Policy {self.id} refuses comparison with "
                        f"industry {candidate}."
                    ),
                    details=(f"subject={self.subject_industry_id}",),
                ),
            )

        if candidate == self.subject_industry_id:
            if self.require_same_business_model_for_direct:
                if (
                    not subject_business_model_id
                    or not candidate_business_model_id
                ):
                    return (
                        PeerEligibilityStatus.INSUFFICIENT_DATA,
                        PeerEligibilityReason(
                            code="missing_business_model",
                            message=(
                                "Same-industry direct peers require business "
                                "model on both sides; data is insufficient."
                            ),
                        ),
                    )
                if (
                    subject_business_model_id.strip().lower()
                    != candidate_business_model_id.strip().lower()
                ):
                    if (
                        candidate_business_model_id.strip().lower()
                        in self.related_business_model_ids
                    ):
                        return (
                            PeerEligibilityStatus.RELATED_PEER,
                            PeerEligibilityReason(
                                code="related_business_model",
                                message=(
                                    "Same industry but related (not identical) "
                                    "business model."
                                ),
                            ),
                        )
                    return (
                        PeerEligibilityStatus.LIMITED_COMPARISON,
                        PeerEligibilityReason(
                            code="business_model_mismatch",
                            message=(
                                "Same industry but business models differ; "
                                "only limited comparison permitted."
                            ),
                        ),
                    )
            return (
                self.same_industry_status,
                PeerEligibilityReason(
                    code="same_industry",
                    message=(
                        f"Both instruments share industry "
                        f"{self.subject_industry_id}."
                    ),
                ),
            )

        if candidate in self.related_industry_ids:
            return (
                PeerEligibilityStatus.RELATED_PEER,
                PeerEligibilityReason(
                    code="related_industry",
                    message=(
                        f"Industry {candidate} is related under policy {self.id}."
                    ),
                ),
            )

        if candidate in self.limited_industry_ids:
            return (
                PeerEligibilityStatus.LIMITED_COMPARISON,
                PeerEligibilityReason(
                    code="limited_industry",
                    message=(
                        f"Industry {candidate} allows only limited comparison "
                        f"under policy {self.id}."
                    ),
                ),
            )

        return (
            self.default_status,
            PeerEligibilityReason(
                code="default_policy_outcome",
                message=(
                    f"No explicit rule for industry {candidate}; "
                    f"defaulting to {self.default_status.value}."
                ),
                details=(f"policy={self.id}",),
            ),
        )


@dataclass(frozen=True, slots=True)
class EligibilityOptions:
    """Which eligibility statuses the future Comparison Engine may accept."""

    allow_related: bool = False
    allow_limited: bool = False

    def accepts(self, status: PeerEligibilityStatus) -> bool:
        if status is PeerEligibilityStatus.DIRECT_PEER:
            return True
        if status is PeerEligibilityStatus.RELATED_PEER:
            return self.allow_related
        if status is PeerEligibilityStatus.LIMITED_COMPARISON:
            return self.allow_limited
        return False


@dataclass(frozen=True, slots=True)
class PeerEligibilityResult:
    """Eligibility outcome for one unordered instrument pair."""

    left_key: str
    right_key: str
    status: PeerEligibilityStatus
    reasons: tuple[PeerEligibilityReason, ...]
    left_industry_id: str | None = None
    right_industry_id: str | None = None
    left_policy_id: str | None = None
    right_policy_id: str | None = None
    comparable: bool = False

    def __post_init__(self) -> None:
        left = self.left_key.strip().upper()
        right = self.right_key.strip().upper()
        if not left or not right:
            msg = "instrument keys must not be empty"
            raise ValidationError(msg)
        if not self.reasons:
            msg = "eligibility result must include at least one reason"
            raise ValidationError(msg)
        object.__setattr__(self, "left_key", left)
        object.__setattr__(self, "right_key", right)


@dataclass(frozen=True, slots=True)
class GroupEligibilityResult:
    """Aggregate eligibility for a multi-instrument evaluation."""

    status: GroupEligibilityStatus
    pair_results: tuple[PeerEligibilityResult, ...]
    eligible_keys: tuple[str, ...]
    ineligible_keys: tuple[str, ...]
    exclusions: tuple[str, ...]
    options: EligibilityOptions

    @property
    def eligible_pairs(self) -> tuple[PeerEligibilityResult, ...]:
        return tuple(p for p in self.pair_results if p.comparable)

    @property
    def ineligible_pairs(self) -> tuple[PeerEligibilityResult, ...]:
        return tuple(p for p in self.pair_results if not p.comparable)


@dataclass(frozen=True, slots=True)
class InstrumentIndustryAssignment:
    """Maps an instrument symbol to DSP industry identity (structural only)."""

    symbol: str
    industry_id: str
    business_model_id: str | None = None

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol:
            msg = "symbol must not be empty"
            raise ValidationError(msg)
        industry_id = _normalize_id(self.industry_id, field="industry_id")
        business_model_id = (
            None
            if self.business_model_id is None
            else _normalize_id(self.business_model_id, field="business_model_id")
        )
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "industry_id", industry_id)
        object.__setattr__(self, "business_model_id", business_model_id)


@dataclass(frozen=True, slots=True)
class InstrumentMethodologyResolution:
    """Resolved industry → methodology → peer policy chain for one instrument."""

    symbol: str
    industry_id: str
    methodology_id: str
    methodology_version: str
    peer_policy_id: str
    peer_policy_version: str
    business_model_id: str | None = None
    profile_version: str | None = None


def stricter_status(
    left: PeerEligibilityStatus, right: PeerEligibilityStatus
) -> PeerEligibilityStatus:
    """Return the more restrictive of two statuses."""
    if _STATUS_STRICTNESS[left] >= _STATUS_STRICTNESS[right]:
        return left
    return right


def _unique_ids(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        cleaned = _normalize_id(raw, field=field)
        if cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return tuple(out)
