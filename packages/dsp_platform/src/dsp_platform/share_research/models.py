"""Client share-research records. Gemini output is untrusted until DSP validates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

__all__ = [
    "ShareResearchStatus",
    "ShareResearchCheck",
    "ShareResearchSource",
    "ShareResearchCorporateAction",
    "ShareResearchRecord",
    "ShareResearchRequest",
    "ShareResearchResult",
    "SHARE_RESEARCH_SCHEMA",
]

SHARE_RESEARCH_SCHEMA = "dsp.share_research.v1"


class ShareResearchStatus(StrEnum):
    CURRENT = "CURRENT"
    REFRESH_REQUIRED = "REFRESH_REQUIRED"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"


class ShareResearchCheck(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNRESOLVED = "UNRESOLVED"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True, slots=True)
class ShareResearchSource:
    url: str
    label: str
    accepted: bool
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "label": self.label,
            "accepted": self.accepted,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class ShareResearchCorporateAction:
    action_type: str
    description: str
    effective_date: date | None
    changes_outstanding_shares: bool | None
    consideration: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "description": self.description,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "changes_outstanding_shares": self.changes_outstanding_shares,
            "consideration": self.consideration,
        }


@dataclass(frozen=True, slots=True)
class ShareResearchRecord:
    """Persisted research run. Not a promoted valuation snapshot by itself."""

    research_id: str
    company_name: str
    ticker: str
    isin: str
    exchange: str
    mic: str
    security_type: str
    outstanding_shares: Decimal | None
    as_of: date | None
    effective_date: date | None
    current_through: date | None
    researched_at: datetime
    last_verified_at: datetime
    status: ShareResearchStatus
    stored_previous_share_count: Decimal | None
    stored_previous_as_of: date | None
    stored_previous_current_through: date | None
    primary_sources: tuple[ShareResearchSource, ...]
    evidence: tuple[str, ...]
    corporate_actions: tuple[ShareResearchCorporateAction, ...]
    share_count_effect: str
    identity_check: ShareResearchCheck
    cross_check: ShareResearchCheck
    corporate_action_check: ShareResearchCheck
    confidence: str
    gemini_invoked: bool
    gemini_research_reference: str
    integrity_hash: str
    valuation_eligible: bool
    unresolved_issues: tuple[str, ...]
    created_at: datetime
    updated_at: datetime
    reason: str = ""
    gemini_duration_ms: int | None = None
    stored_record_status: str = ""
    promotion_recommended: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SHARE_RESEARCH_SCHEMA,
            "research_id": self.research_id,
            "company_name": self.company_name,
            "ticker": self.ticker,
            "isin": self.isin,
            "exchange": self.exchange,
            "mic": self.mic,
            "security_type": self.security_type,
            "outstanding_shares": (
                str(self.outstanding_shares)
                if self.outstanding_shares is not None
                else None
            ),
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "effective_date": (
                self.effective_date.isoformat() if self.effective_date else None
            ),
            "current_through": (
                self.current_through.isoformat() if self.current_through else None
            ),
            "researched_at": self.researched_at.isoformat(),
            "last_verified_at": self.last_verified_at.isoformat(),
            "status": str(self.status),
            "stored_previous_share_count": (
                str(self.stored_previous_share_count)
                if self.stored_previous_share_count is not None
                else None
            ),
            "stored_previous_as_of": (
                self.stored_previous_as_of.isoformat()
                if self.stored_previous_as_of
                else None
            ),
            "stored_previous_current_through": (
                self.stored_previous_current_through.isoformat()
                if self.stored_previous_current_through
                else None
            ),
            "primary_sources": [row.to_dict() for row in self.primary_sources],
            "evidence": list(self.evidence),
            "corporate_actions": [row.to_dict() for row in self.corporate_actions],
            "share_count_effect": self.share_count_effect,
            "identity_check": str(self.identity_check),
            "cross_check": str(self.cross_check),
            "corporate_action_check": str(self.corporate_action_check),
            "confidence": self.confidence,
            "gemini_invoked": self.gemini_invoked,
            "gemini_research_reference": self.gemini_research_reference,
            "integrity_hash": self.integrity_hash,
            "valuation_eligible": self.valuation_eligible,
            "unresolved_issues": list(self.unresolved_issues),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "reason": self.reason,
            "gemini_duration_ms": self.gemini_duration_ms,
            "stored_record_status": self.stored_record_status,
            "promotion_recommended": self.promotion_recommended,
        }


@dataclass(frozen=True, slots=True)
class ShareResearchRequest:
    ticker: str
    exchange: str | None = None
    company: str | None = None
    isin: str | None = None
    mic: str | None = None
    lookup_horizon: datetime | None = None
    force_refresh: bool = False


@dataclass(frozen=True, slots=True)
class ShareResearchResult:
    record: ShareResearchRecord
    history: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    gemini_invoked: bool = False

    def to_client_dict(self) -> dict[str, Any]:
        rec = self.record
        stored = rec.stored_previous_share_count
        fresh = rec.outstanding_shares
        match = (
            stored is not None
            and fresh is not None
            and stored == fresh
        )
        return {
            "schema_version": SHARE_RESEARCH_SCHEMA,
            "research_id": rec.research_id,
            "status": str(rec.status),
            "company": rec.company_name,
            "ticker": rec.ticker,
            "isin": rec.isin,
            "exchange": rec.exchange,
            "mic": rec.mic,
            "security_type": rec.security_type,
            "outstanding_shares": (
                int(fresh) if fresh is not None and fresh == fresh.to_integral_value()
                else (str(fresh) if fresh is not None else None)
            ),
            "as_of": rec.as_of.isoformat() if rec.as_of else None,
            "current_through": (
                rec.current_through.isoformat() if rec.current_through else None
            ),
            "last_verified_at": rec.last_verified_at.isoformat(),
            "confidence": rec.confidence,
            "identity_check": str(rec.identity_check),
            "corporate_action_check": str(rec.corporate_action_check),
            "cross_check": str(rec.cross_check),
            "valuation_eligible": rec.valuation_eligible,
            "share_count_effect": rec.share_count_effect,
            "gemini_invoked": self.gemini_invoked,
            "reason": rec.reason,
            "unresolved_issues": list(rec.unresolved_issues),
            "stored_vs_fresh": {
                "stored": str(stored) if stored is not None else None,
                "fresh": str(fresh) if fresh is not None else None,
                "result": "MATCH" if match else ("CHANGED" if stored and fresh else "N/A"),
            },
            "evidence": [row.to_dict() for row in rec.primary_sources],
            "corporate_actions": [row.to_dict() for row in rec.corporate_actions],
            "research_history": list(self.history),
            "research_method": (
                "Gemini primary-source research with DSP validation"
                if self.gemini_invoked
                else "Stored DSP research record proven current at lookup horizon"
            ),
            "promotion_recommended": rec.promotion_recommended,
        }
