"""Share-research engine: stored record → Gemini if needed → DSP validation."""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from dsp_platform.current_outstanding_protocol.currentness import (
    CorporateActionCurrentnessEvidence,
    ShareChangingCorporateAction,
    evaluate_option_b_currentness,
)
from dsp_platform.share_count_refresh import InstrumentIdentity
from dsp_platform.share_research.gemini import (
    ShareResearchGeminiError,
    ShareResearchGeminiPort,
)
from dsp_platform.share_research.identity import resolve_research_identity
from dsp_platform.share_research.models import (
    ShareResearchCheck,
    ShareResearchRecord,
    ShareResearchRequest,
    ShareResearchResult,
    ShareResearchStatus,
)
from dsp_platform.share_research.store import ShareResearchStore, get_share_research_store
from dsp_platform.share_research.validation import (
    ValidatedGeminiResearch,
    parse_gemini_payload,
    validate_gemini_research,
)

__all__ = ["ShareResearchEngine", "research_shares"]

_LOG = logging.getLogger("dsp.share_research")
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_for(isin: str) -> threading.Lock:
    key = isin.strip().upper()
    with _LOCKS_GUARD:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


class ShareResearchEngine:
    def __init__(
        self,
        *,
        store: ShareResearchStore | None = None,
        gemini: ShareResearchGeminiPort | None = None,
    ) -> None:
        self._store = store or get_share_research_store()
        self._gemini = gemini

    def research(self, request: ShareResearchRequest) -> ShareResearchResult:
        identity = resolve_research_identity(request)
        horizon = request.lookup_horizon or datetime.now(tz=UTC)
        if horizon.tzinfo is None:
            horizon = horizon.replace(tzinfo=UTC)
        if identity is None or not identity.isin or not identity.mic:
            record = self._terminal(
                identity=identity
                or InstrumentIdentity(
                    symbol=str(request.ticker or ""),
                    exchange=str(request.exchange or ""),
                    mic="",
                    isin="",
                ),
                horizon=horizon,
                status=ShareResearchStatus.UNKNOWN,
                reason="identity could not be resolved",
                identity_check=ShareResearchCheck.FAIL,
            )
            return ShareResearchResult(record=record, history=(), gemini_invoked=False)
        with _lock_for(identity.isin):
            return self._research_locked(request, identity, horizon)

    def _research_locked(
        self,
        request: ShareResearchRequest,
        identity: InstrumentIdentity,
        horizon: datetime,
    ) -> ShareResearchResult:
        stored = self._store.load_current(identity.isin)
        history = self._store.load_history(identity.isin)
        stored_status = self._stored_currentness(stored, identity, horizon)
        if (
            stored is not None
            and stored_status is ShareResearchStatus.CURRENT
            and not request.force_refresh
        ):
            reused = _reuse_current_record(stored, horizon)
            _LOG.info(
                "share_research skip_gemini research_id=%s isin=%s status=CURRENT",
                reused.research_id,
                identity.isin,
            )
            return ShareResearchResult(
                record=reused, history=history, gemini_invoked=False
            )
        if self._gemini is None:
            record = self._persist(
                self._terminal(
                    identity=identity,
                    horizon=horizon,
                    status=ShareResearchStatus.REFRESH_REQUIRED,
                    reason=(
                        "stored share count is not proven current; "
                        "Gemini is not configured"
                    ),
                    stored=stored,
                    identity_check=ShareResearchCheck.PASS,
                )
            )
            return ShareResearchResult(
                record=record, history=history, gemini_invoked=False
            )
        _LOG.info(
            "share_research stage=gemini_start isin=%s ticker=%s adapter=%s",
            identity.isin,
            identity.symbol,
            type(self._gemini).__name__,
        )
        try:
            gemini = self._gemini.research(
                identity=identity,
                stored=stored.to_dict() if stored is not None else None,
                horizon_iso=horizon.isoformat(),
                user_prompt=_user_prompt(identity, stored, horizon),
            )
        except ShareResearchGeminiError as exc:
            status = ShareResearchStatus.UNKNOWN
            if exc.kind in {
                "timeout",
                "rate_limited",
                "http_5xx",
                "http_4xx",
                "unavailable",
                "empty",
            }:
                status = ShareResearchStatus.REFRESH_REQUIRED
            if exc.kind == "malformed":
                status = ShareResearchStatus.INVALID
            record = self._persist(
                self._terminal(
                    identity=identity,
                    horizon=horizon,
                    status=status,
                    reason=f"Gemini research failed ({exc.kind})",
                    stored=stored,
                    identity_check=ShareResearchCheck.PASS,
                    gemini_invoked=True,
                    gemini_duration_ms=None,
                )
            )
            _LOG.warning(
                "share_research gemini_error kind=%s isin=%s status=%s",
                exc.kind,
                identity.isin,
                status,
            )
            return ShareResearchResult(
                record=record, history=history, gemini_invoked=True
            )
        parsed = parse_gemini_payload(gemini.payload)
        if parsed is None:
            record = self._persist(
                self._terminal(
                    identity=identity,
                    horizon=horizon,
                    status=ShareResearchStatus.INVALID,
                    reason="Gemini response failed schema validation",
                    stored=stored,
                    identity_check=ShareResearchCheck.PASS,
                    gemini_invoked=True,
                    gemini_duration_ms=gemini.duration_ms,
                )
            )
            return ShareResearchResult(
                record=record, history=history, gemini_invoked=True
            )
        claimed_status = str(parsed.get("STATUS") or "").strip().upper()
        validated = validate_gemini_research(
            parsed,
            identity=identity,
            extra_issuer_hosts=_issuer_hosts(identity),
        )
        record = self._record_from_validated(
            identity=identity,
            horizon=horizon,
            stored=stored,
            validated=validated,
            gemini_duration_ms=gemini.duration_ms,
            gemini_reference=gemini.reference,
            claimed_status=claimed_status,
        )
        saved = self._persist(record)
        accepted = sum(1 for row in saved.primary_sources if row.accepted)
        rejected = sum(1 for row in saved.primary_sources if not row.accepted)
        _LOG.info(
            "share_research complete research_id=%s isin=%s ticker=%s status=%s "
            "gemini=1 duration_ms=%s sources_accepted=%s sources_rejected=%s "
            "ca_check=%s currentness=%s valuation_eligible=%s reason=%s",
            saved.research_id,
            identity.isin,
            identity.symbol,
            saved.status,
            gemini.duration_ms,
            accepted,
            rejected,
            saved.corporate_action_check,
            saved.status,
            saved.valuation_eligible,
            saved.reason,
        )
        return ShareResearchResult(
            record=saved,
            history=self._store.load_history(identity.isin),
            gemini_invoked=True,
        )

    def _stored_currentness(
        self,
        stored: ShareResearchRecord | None,
        identity: InstrumentIdentity,
        horizon: datetime,
    ) -> ShareResearchStatus | None:
        if stored is None:
            return None
        if stored.identity_check is not ShareResearchCheck.PASS:
            return ShareResearchStatus.UNKNOWN
        if stored.isin != identity.isin:
            return ShareResearchStatus.INVALID
        if stored.status is ShareResearchStatus.CONFLICT:
            return ShareResearchStatus.CONFLICT
        if stored.outstanding_shares is None or stored.as_of is None:
            return ShareResearchStatus.UNKNOWN
        if stored.corporate_action_check is ShareResearchCheck.UNRESOLVED:
            return ShareResearchStatus.UNKNOWN
        evidence = _evidence_from_record(stored)
        if evidence is None:
            return ShareResearchStatus.REFRESH_REQUIRED
        verdict = evaluate_option_b_currentness(
            share_count_as_of=stored.as_of,
            retrieved_at=horizon,
            evidence=evidence,
        )
        if verdict.proven:
            return ShareResearchStatus.CURRENT
        if "does not reach retrieved_at" in verdict.reason:
            return ShareResearchStatus.REFRESH_REQUIRED
        if "not classified" in verdict.reason:
            return ShareResearchStatus.UNKNOWN
        return ShareResearchStatus.REFRESH_REQUIRED

    def _persist(self, record: ShareResearchRecord) -> ShareResearchRecord:
        self._store.save(record)
        return record

    def _record_from_validated(
        self,
        *,
        identity: InstrumentIdentity,
        horizon: datetime,
        stored: ShareResearchRecord | None,
        validated: ValidatedGeminiResearch,
        gemini_duration_ms: int,
        gemini_reference: str,
        claimed_status: str,
    ) -> ShareResearchRecord:
        status, reason = _decide_status(validated, horizon, claimed_status)
        if validated.identity_check is ShareResearchCheck.FAIL:
            status = ShareResearchStatus.INVALID
            reason = "identity mismatch"
        valuation_ok = (
            status is ShareResearchStatus.CURRENT
            and validated.identity_check is ShareResearchCheck.PASS
            and validated.cross_check is ShareResearchCheck.PASS
            and validated.corporate_action_check is ShareResearchCheck.PASS
            and validated.shares is not None
        )
        current_through = (
            validated.ca_coverage_end
            if status is ShareResearchStatus.CURRENT
            else validated.claimed_current_through
        )
        body = {
            "ticker": identity.symbol,
            "isin": identity.isin,
            "shares": str(validated.shares) if validated.shares is not None else None,
            "as_of": validated.as_of.isoformat() if validated.as_of else None,
            "current_through": (
                current_through.isoformat() if current_through else None
            ),
            "status": str(status),
        }
        digest = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return ShareResearchRecord(
            research_id=str(uuid.uuid4()),
            company_name=validated.company or identity.issuer or identity.symbol,
            ticker=identity.symbol,
            isin=identity.isin,
            exchange=identity.exchange,
            mic=identity.mic,
            security_type=identity.security_type or "common_equity",
            outstanding_shares=validated.shares,
            as_of=validated.as_of,
            effective_date=validated.as_of,
            current_through=current_through,
            researched_at=horizon,
            last_verified_at=horizon,
            status=status,
            stored_previous_share_count=(
                stored.outstanding_shares if stored is not None else None
            ),
            stored_previous_as_of=stored.as_of if stored is not None else None,
            stored_previous_current_through=(
                stored.current_through if stored is not None else None
            ),
            primary_sources=validated.sources,
            evidence=validated.evidence,
            corporate_actions=validated.actions,
            share_count_effect=validated.share_count_effect,
            identity_check=validated.identity_check,
            cross_check=validated.cross_check,
            corporate_action_check=validated.corporate_action_check,
            confidence="HIGH" if valuation_ok else validated.confidence,
            gemini_invoked=True,
            gemini_research_reference=gemini_reference,
            integrity_hash=digest,
            valuation_eligible=valuation_ok,
            unresolved_issues=validated.issues,
            created_at=horizon,
            updated_at=horizon,
            reason=reason,
            gemini_duration_ms=gemini_duration_ms,
            stored_record_status=(
                str(stored.status) if stored is not None else "ABSENT"
            ),
            promotion_recommended=valuation_ok,
        )

    def _terminal(
        self,
        *,
        identity: InstrumentIdentity,
        horizon: datetime,
        status: ShareResearchStatus,
        reason: str,
        stored: ShareResearchRecord | None = None,
        identity_check: ShareResearchCheck = ShareResearchCheck.NOT_RUN,
        gemini_invoked: bool = False,
        gemini_duration_ms: int | None = None,
    ) -> ShareResearchRecord:
        return ShareResearchRecord(
            research_id=str(uuid.uuid4()),
            company_name=identity.issuer or identity.symbol,
            ticker=identity.symbol,
            isin=identity.isin,
            exchange=identity.exchange,
            mic=identity.mic,
            security_type=identity.security_type or "common_equity",
            outstanding_shares=stored.outstanding_shares if stored else None,
            as_of=stored.as_of if stored else None,
            effective_date=stored.effective_date if stored else None,
            current_through=stored.current_through if stored else None,
            researched_at=horizon,
            last_verified_at=horizon,
            status=status,
            stored_previous_share_count=stored.outstanding_shares if stored else None,
            stored_previous_as_of=stored.as_of if stored else None,
            stored_previous_current_through=stored.current_through if stored else None,
            primary_sources=stored.primary_sources if stored else (),
            evidence=stored.evidence if stored else (),
            corporate_actions=stored.corporate_actions if stored else (),
            share_count_effect="",
            identity_check=identity_check,
            cross_check=ShareResearchCheck.NOT_RUN,
            corporate_action_check=ShareResearchCheck.NOT_RUN,
            confidence="LOW",
            gemini_invoked=gemini_invoked,
            gemini_research_reference="",
            integrity_hash="",
            valuation_eligible=False,
            unresolved_issues=(reason,),
            created_at=horizon,
            updated_at=horizon,
            reason=reason,
            gemini_duration_ms=gemini_duration_ms,
            stored_record_status=str(stored.status) if stored else "ABSENT",
            promotion_recommended=False,
        )


def research_shares(
    request: ShareResearchRequest,
    *,
    engine: ShareResearchEngine | None = None,
) -> ShareResearchResult:
    return (engine or ShareResearchEngine()).research(request)


def _decide_status(
    validated: ValidatedGeminiResearch,
    horizon: datetime,
    claimed_status: str,
) -> tuple[ShareResearchStatus, str]:
    if claimed_status == "CONFLICT" or any(
        "conflict" in item.casefold() for item in validated.issues
    ):
        return ShareResearchStatus.CONFLICT, "conflicting authoritative evidence"
    if validated.identity_check is ShareResearchCheck.FAIL:
        return ShareResearchStatus.INVALID, "identity mismatch"
    if validated.shares is None or validated.as_of is None:
        return ShareResearchStatus.UNKNOWN, "outstanding shares could not be established"
    if validated.corporate_action_check is ShareResearchCheck.UNRESOLVED:
        return (
            ShareResearchStatus.UNKNOWN,
            "corporate-action consideration or classification is unresolved",
        )
    if validated.cross_check is ShareResearchCheck.FAIL:
        return (
            ShareResearchStatus.UNKNOWN,
            "approved primary cross-check is incomplete",
        )
    if not validated.ca_pagination_exhausted or validated.ca_coverage_end is None:
        return (
            ShareResearchStatus.REFRESH_REQUIRED,
            "corporate-action coverage is not proven through the lookup horizon",
        )
    if validated.ca_coverage_end < horizon.date():
        return (
            ShareResearchStatus.REFRESH_REQUIRED,
            "corporate-action coverage does not reach the lookup horizon",
        )
    if validated.as_of > horizon.date():
        return ShareResearchStatus.INVALID, "share-count as_of is after the lookup horizon"
    source_url = next((row.url for row in validated.sources if row.accepted), "")
    if not source_url:
        return ShareResearchStatus.UNKNOWN, "no approved primary source URL"
    evidence = CorporateActionCurrentnessEvidence(
        events=tuple(
            ShareChangingCorporateAction(
                action_type=row.action_type,
                effective_date=row.effective_date,
                changes_outstanding_shares=row.changes_outstanding_shares,
                already_reflected_in_share_count=False,
                description=row.description,
            )
            for row in validated.actions
        ),
        complete_through=validated.ca_coverage_end,
        share_count_as_of=validated.as_of,
        source_tier="TIER_1_PRIMARY",
        source_url=source_url,
        evidence_reference="DSP-validated Gemini primary-source share research",
    )
    verdict = evaluate_option_b_currentness(
        share_count_as_of=validated.as_of,
        retrieved_at=horizon,
        evidence=evidence,
    )
    if verdict.proven:
        return ShareResearchStatus.CURRENT, verdict.reason
    if "does not reach" in verdict.reason or "later share-changing" in verdict.reason:
        return ShareResearchStatus.REFRESH_REQUIRED, verdict.reason
    return ShareResearchStatus.UNKNOWN, verdict.reason


def _evidence_from_record(
    stored: ShareResearchRecord,
) -> CorporateActionCurrentnessEvidence | None:
    if stored.as_of is None or stored.current_through is None:
        return None
    source_url = next((row.url for row in stored.primary_sources if row.accepted), "")
    if not source_url:
        return None
    return CorporateActionCurrentnessEvidence(
        events=tuple(
            ShareChangingCorporateAction(
                action_type=row.action_type,
                effective_date=row.effective_date,
                changes_outstanding_shares=row.changes_outstanding_shares,
                already_reflected_in_share_count=False,
                description=row.description,
            )
            for row in stored.corporate_actions
        ),
        complete_through=stored.current_through,
        share_count_as_of=stored.as_of,
        source_tier="TIER_1_PRIMARY",
        source_url=source_url,
        evidence_reference="stored DSP share-research record",
    )


def _issuer_hosts(identity: InstrumentIdentity) -> frozenset[str]:
    try:
        from dsp_platform.share_count_acquisition.universe import get_listed_equity

        row = get_listed_equity(identity.isin, identity.mic)
        if row is None and identity.mic == "XNSE":
            row = get_listed_equity(identity.isin, "XBOM")
        if row is None:
            return frozenset()
        return row.ir_hosts
    except Exception:  # noqa: BLE001
        return frozenset()


def _user_prompt(
    identity: InstrumentIdentity,
    stored: ShareResearchRecord | None,
    horizon: datetime,
) -> str:
    stored_block: Any = stored.to_dict() if stored is not None else None
    return (
        "Research CURRENT OUTSTANDING EQUITY SHARES for this security.\n"
        f"ticker={identity.symbol}\n"
        f"exchange={identity.exchange}\n"
        f"mic={identity.mic}\n"
        f"isin={identity.isin}\n"
        f"company={identity.issuer}\n"
        f"requested_horizon={horizon.date().isoformat()}\n"
        f"stored_record={json.dumps(stored_block, default=str) if stored_block else 'null'}\n"
    )


def _reuse_current_record(
    stored: ShareResearchRecord, horizon: datetime
) -> ShareResearchRecord:
    return ShareResearchRecord(
        research_id=stored.research_id,
        company_name=stored.company_name,
        ticker=stored.ticker,
        isin=stored.isin,
        exchange=stored.exchange,
        mic=stored.mic,
        security_type=stored.security_type,
        outstanding_shares=stored.outstanding_shares,
        as_of=stored.as_of,
        effective_date=stored.effective_date,
        current_through=stored.current_through,
        researched_at=stored.researched_at,
        last_verified_at=horizon,
        status=ShareResearchStatus.CURRENT,
        stored_previous_share_count=stored.outstanding_shares,
        stored_previous_as_of=stored.as_of,
        stored_previous_current_through=stored.current_through,
        primary_sources=stored.primary_sources,
        evidence=stored.evidence,
        corporate_actions=stored.corporate_actions,
        share_count_effect=stored.share_count_effect,
        identity_check=stored.identity_check,
        cross_check=stored.cross_check,
        corporate_action_check=stored.corporate_action_check,
        confidence=stored.confidence,
        gemini_invoked=False,
        gemini_research_reference=stored.gemini_research_reference,
        integrity_hash=stored.integrity_hash,
        valuation_eligible=True,
        unresolved_issues=(),
        created_at=stored.created_at,
        updated_at=horizon,
        reason="stored research record is Option-B current at lookup horizon",
        gemini_duration_ms=None,
        stored_record_status="CURRENT",
        promotion_recommended=False,
    )
