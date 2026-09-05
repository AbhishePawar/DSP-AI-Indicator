"""Deterministic Option B currentness for current outstanding shares.

Gemini cannot approve currentness. Missing corporate-action completeness
is OPTION_B_UNPROVEN — not a snapshot.

``retrieved_at``, publication date, and filing date are never treated as
the share-count ``as_of`` or as an event ``effective_date``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from data_engine import AuthenticatedCorporateAction

__all__ = [
    "CorporateActionCurrentnessEvidence",
    "OPTION_B_UNPROVEN",
    "OptionBCurrentnessVerdict",
    "SHARE_CHANGING_ACTION_TYPES",
    "ShareChangingCorporateAction",
    "evaluate_option_b_currentness",
    "share_changing_event_from_authenticated_action",
]

OPTION_B_UNPROVEN = "OPTION_B_UNPROVEN"

SHARE_CHANGING_ACTION_TYPES = frozenset(
    {
        "stock_split",
        "split",
        "reverse_split",
        "bonus",
        "bonus_issue",
        "rights",
        "rights_issue",
        "new_issue",
        "buyback",
        "cancellation",
        "merger",
        "demerger",
        "conversion",
        "share_capital_change",
        "treasury",
        "treasury_share_change",
        "buyback_extinguishment",
        "allotment",
        "acquisition_share_swap",
        "acquisition_share_consideration",
        "acquisition_mixed_consideration",
        "cancellation",
    }
)
_KNOWN_NON_CHANGING = frozenset(
    {
        "dividend",
        "symbol_change",
        "board_announcement",
        "non_capital_disclosure",
        "acquisition_cash",
        "acquisition_completion",
    }
)
_ADMISSIBLE_CA_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY"})


@dataclass(frozen=True, slots=True)
class ShareChangingCorporateAction:
    """Minimum event needed to ask whether outstanding shares still hold."""

    action_type: str
    effective_date: date | None
    changes_outstanding_shares: bool | None = None
    already_reflected_in_share_count: bool | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "effective_date": (
                self.effective_date.isoformat()
                if self.effective_date is not None
                else None
            ),
            "changes_outstanding_shares": self.changes_outstanding_shares,
            "already_reflected_in_share_count": (
                self.already_reflected_in_share_count
            ),
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class CorporateActionCurrentnessEvidence:
    """DSP-owned CA completeness evidence. Absence is not proof of none."""

    events: tuple[ShareChangingCorporateAction, ...]
    complete_through: date | None
    share_count_as_of: date
    source_tier: str
    source_url: str
    evidence_reference: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [event.to_dict() for event in self.events],
            "complete_through": (
                self.complete_through.isoformat()
                if self.complete_through is not None
                else None
            ),
            "share_count_as_of": self.share_count_as_of.isoformat(),
            "source_tier": self.source_tier,
            "source_url": self.source_url,
            "evidence_reference": self.evidence_reference,
        }


@dataclass(frozen=True, slots=True)
class OptionBCurrentnessVerdict:
    proven: bool
    reason: str
    later_share_changing_event: ShareChangingCorporateAction | None = None

    def to_dict(self) -> dict[str, Any]:
        later = self.later_share_changing_event
        return {
            "proven": self.proven,
            "reason": self.reason,
            "later_share_changing_event": None if later is None else later.to_dict(),
        }


def share_changing_event_from_authenticated_action(
    action: AuthenticatedCorporateAction,
) -> ShareChangingCorporateAction:
    """Project an existing CA event. Does not invent currentness."""
    action_type = str(action.action_type or "").strip().lower()
    changes: bool | None
    if action_type in SHARE_CHANGING_ACTION_TYPES:
        changes = True
    elif action_type in _KNOWN_NON_CHANGING:
        changes = False
    else:
        changes = None
    return ShareChangingCorporateAction(
        action_type=action_type,
        effective_date=action.effective_date,
        changes_outstanding_shares=changes,
        already_reflected_in_share_count=None,
        description=action.description,
    )


def evaluate_option_b_currentness(
    *,
    share_count_as_of: date,
    retrieved_at: datetime,
    evidence: CorporateActionCurrentnessEvidence | None,
) -> OptionBCurrentnessVerdict:
    """Prove latest corporate-action-adjusted outstanding, or fail closed."""
    if not isinstance(share_count_as_of, date) or isinstance(
        share_count_as_of, datetime
    ):
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="share-count as_of is required and must be a date, not retrieved_at",
        )
    if not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="retrieved_at must be timezone-aware and is not as_of",
        )
    horizon = retrieved_at.date()
    if share_count_as_of > horizon:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason=(
                "share-count as_of is after retrieved_at; "
                "future observations are unproven"
            ),
        )
    if evidence is None:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action completeness is unavailable",
        )
    if not isinstance(evidence.share_count_as_of, date) or isinstance(
        evidence.share_count_as_of, datetime
    ):
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action evidence as_of is not a date",
        )
    if evidence.share_count_as_of != share_count_as_of:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action evidence as_of does not match share-count as_of",
        )
    tier = str(evidence.source_tier or "").strip()
    if tier not in _ADMISSIBLE_CA_TIERS:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action evidence is not an admissible source tier",
        )
    if not str(evidence.source_url or "").strip():
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action evidence source_url is required",
        )
    if not str(evidence.evidence_reference or "").strip():
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action evidence_reference is required",
        )
    if evidence.complete_through is None:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action complete_through date is missing",
        )
    if not isinstance(evidence.complete_through, date) or isinstance(
        evidence.complete_through, datetime
    ):
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="complete_through must be a date, not retrieved_at",
        )
    if evidence.complete_through < evidence.share_count_as_of:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="complete_through is before share-count as_of",
        )
    if evidence.complete_through < horizon:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason=(
                "corporate-action coverage does not reach retrieved_at; "
                "Option B currentness is unproven"
            ),
        )
    for event in evidence.events:
        verdict = _event_blocks_currentness(
            event, share_count_as_of=share_count_as_of, horizon=horizon
        )
        if verdict is not None:
            return verdict
    return OptionBCurrentnessVerdict(
        proven=True,
        reason="no later share-changing corporate action after share-count as_of",
    )


def _event_blocks_currentness(
    event: ShareChangingCorporateAction,
    *,
    share_count_as_of: date,
    horizon: date,
) -> OptionBCurrentnessVerdict | None:
    action_type = str(event.action_type or "").strip().lower()
    if not action_type:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="corporate-action type is missing",
            later_share_changing_event=event,
        )
    changes = event.changes_outstanding_shares
    if changes is None:
        if action_type in SHARE_CHANGING_ACTION_TYPES:
            changes = True
        elif action_type in _KNOWN_NON_CHANGING:
            changes = False
        else:
            return OptionBCurrentnessVerdict(
                proven=False,
                reason=f"corporate-action type {action_type!r} is not classified",
                later_share_changing_event=event,
            )
    if changes is False:
        return None
    if event.effective_date is None:
        return OptionBCurrentnessVerdict(
            proven=False,
            reason="share-changing corporate action is missing effective_date",
            later_share_changing_event=event,
        )
    if event.effective_date > horizon:
        # Announced or scheduled, not yet effective at the lookup horizon.
        return None
    if event.effective_date <= share_count_as_of:
        return None
    if event.already_reflected_in_share_count is True:
        return None
    return OptionBCurrentnessVerdict(
        proven=False,
        reason=(
            "later share-changing corporate action after share-count as_of "
            "is not proven reflected"
        ),
        later_share_changing_event=event,
    )
