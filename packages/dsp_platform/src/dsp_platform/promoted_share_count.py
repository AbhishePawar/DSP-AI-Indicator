"""Durable promoted ShareCountPort — validated snapshots, no runtime research.

Research/evidence acquisition happens offline. This adapter loads signed
JSON snapshots, checks identity + Option B currentness, and returns a
``ShareCountSnapshot`` or fails closed. It does not call Gemini, scrape
the web, derive shares from price/market cap, or use float / WAS.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from contracts.domain.instrument import Instrument
from data_engine import (
    ShareCountBasis,
    ShareCountField,
    ShareCountPort,
    ShareCountProvenance,
    ShareCountProviderHealth,
    ShareCountSnapshot,
    ShareCountUnit,
    assert_share_count_identity,
    validate_share_count_snapshot,
)
from dsp_platform.current_outstanding_protocol.currentness import (
    CorporateActionCurrentnessEvidence,
    ShareChangingCorporateAction,
    evaluate_option_b_currentness,
)

__all__ = [
    "DEFAULT_PROMOTED_SHARE_COUNT_DIR",
    "DurablePromotedShareCountAdapter",
    "SHARES_OUTSTANDING_CONFLICT",
    "SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN",
    "SHARES_OUTSTANDING_IDENTITY_MISMATCH",
    "SHARES_OUTSTANDING_STALE",
    "SHARES_OUTSTANDING_TAMPERED",
    "SHARES_OUTSTANDING_UNAVAILABLE",
    "ShareCountResolutionError",
    "canonical_promoted_snapshot_digest",
    "horizon_now",
    "load_promoted_share_count_records",
    "sign_promoted_snapshot",
]

SHARES_OUTSTANDING_UNAVAILABLE = "SHARES_OUTSTANDING_UNAVAILABLE"
SHARES_OUTSTANDING_IDENTITY_MISMATCH = "SHARES_OUTSTANDING_IDENTITY_MISMATCH"
SHARES_OUTSTANDING_STALE = "SHARES_OUTSTANDING_STALE"
SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN = "SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN"
SHARES_OUTSTANDING_CONFLICT = "SHARES_OUTSTANDING_CONFLICT"
SHARES_OUTSTANDING_TAMPERED = "SHARES_OUTSTANDING_TAMPERED"

DEFAULT_PROMOTED_SHARE_COUNT_DIR = (
    Path(__file__).resolve().parent / "promoted_share_counts"
)

_PROVIDER_ID = "promoted_t1_share_count"
_ADMISSIBLE_TIERS = frozenset({"TIER_1_PRIMARY", "TIER_2_SECONDARY"})
_EXCHANGE_TO_MIC = {
    "NSE": "XNSE",
    "BSE": "XBOM",
    "NYSE": "XNYS",
    "NASDAQ": "XNAS",
}
_EQUIVALENT_MIC_GROUPS = (frozenset({"XNSE", "XBOM"}),)
_FORBIDDEN_SHARE_KEYS = frozenset(
    {
        "float",
        "free_float",
        "free_float_shares",
        "float_shares",
        "weighted_average",
        "weighted_average_shares",
        "weighted_average_shares_basic",
        "weighted_average_shares_diluted",
        "basic_weighted_average_shares",
        "diluted_weighted_average_shares",
        "market_cap_implied_shares",
        "implied_shares",
        "issued",
        "issued_shares",
        "authorized",
        "authorized_shares",
        "treasury",
        "treasury_shares",
        "diluted",
        "diluted_shares",
    }
)


class ShareCountResolutionError(Exception):
    """Fail-closed share-count lookup with a stable diagnostic code."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = str(code)
        self.detail = str(detail or "")
        message = self.code if not self.detail else f"{self.code}: {self.detail}"
        super().__init__(message)


def horizon_now() -> datetime:
    """Timezone-aware lookup horizon. Never used as share-count as_of."""
    return datetime.now(tz=UTC)


def canonical_promoted_snapshot_digest(payload: Mapping[str, Any]) -> str:
    """SHA-256 over canonical JSON excluding the integrity envelope."""
    body = {key: value for key, value in payload.items() if key != "integrity"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def sign_promoted_snapshot(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with a canonical integrity digest. Test/promotion helper."""
    signed = dict(payload)
    signed.pop("integrity", None)
    signed["integrity"] = {"sha256": canonical_promoted_snapshot_digest(signed)}
    return signed


def _norm(value: object | None) -> str:
    return str(value or "").strip().upper()


def _parse_iso_date(raw: object, *, field: str) -> date:
    if isinstance(raw, datetime):
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            f"{field} must be a date, not retrieved_at",
        )
    if isinstance(raw, date):
        return raw
    text = str(raw or "").strip()
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            f"{field} must be an ISO date",
        ) from exc


def _mics_equivalent(left: str, right: str) -> bool:
    if left == right:
        return True
    pair = frozenset({left, right})
    return any(pair <= group for group in _EQUIVALENT_MIC_GROUPS)


@dataclass(frozen=True, slots=True)
class _PromotedRecord:
    snapshot: ShareCountSnapshot
    as_of: date
    complete_through: date
    source_tier: str
    source_url: str
    evidence_reference: str
    events: tuple[ShareChangingCorporateAction, ...]
    mic: str
    shares: Decimal


def _reject_forbidden_keys(payload: Mapping[str, Any]) -> None:
    keys = {str(key).strip().lower() for key in payload}
    bad = keys & _FORBIDDEN_SHARE_KEYS
    if bad:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "float/WAS/implied share fields cannot become current outstanding",
        )


def _record_from_payload(payload: Mapping[str, Any]) -> _PromotedRecord:
    _reject_forbidden_keys(payload)
    expected = str(
        (payload.get("integrity") or {}).get("sha256")
        if isinstance(payload.get("integrity"), Mapping)
        else ""
    ).strip().lower()
    digest = canonical_promoted_snapshot_digest(payload)
    if not expected or digest != expected:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_TAMPERED,
            "promoted snapshot integrity digest mismatch",
        )

    identity = payload.get("identity")
    if not isinstance(identity, Mapping):
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_IDENTITY_MISMATCH,
            "promoted snapshot identity is required",
        )
    symbol = _norm(identity.get("symbol"))
    exchange = _norm(identity.get("exchange"))
    isin = _norm(identity.get("isin"))
    mic = _norm(identity.get("mic"))
    if not symbol or not exchange or not isin or not mic:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_IDENTITY_MISMATCH,
            "promoted snapshot requires symbol, exchange, MIC, and ISIN",
        )

    basis = str(payload.get("basis") or "").strip().lower()
    unit = str(payload.get("unit") or "").strip().lower()
    if basis != ShareCountBasis.CURRENT_OUTSTANDING.value:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "only current_outstanding basis may be promoted",
        )
    if unit != ShareCountUnit.SHARES.value:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "promoted share count unit must be shares",
        )
    if payload.get("corporate_action_adjusted") is not True:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "promoted snapshot must be corporate-action adjusted",
        )

    try:
        shares = Decimal(str(payload.get("shares_outstanding")))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "shares_outstanding must be numeric",
        ) from exc
    if not shares.is_finite() or shares <= 0:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "shares_outstanding must be > 0",
        )

    as_of = _parse_iso_date(payload.get("as_of"), field="as_of")
    effective = _parse_iso_date(
        payload.get("effective_date") or payload.get("as_of"),
        field="effective_date",
    )
    complete_through = _parse_iso_date(
        payload.get("complete_through"), field="complete_through"
    )
    source_tier = str(payload.get("source_tier") or "").strip()
    if source_tier not in _ADMISSIBLE_TIERS:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "promoted snapshot source_tier is not admissible",
        )
    source = payload.get("source")
    if not isinstance(source, Mapping):
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "promoted snapshot source provenance is required",
        )
    source_url = str(source.get("source_url") or "").strip()
    evidence_reference = str(source.get("evidence_reference") or "").strip()
    if not source_url or not evidence_reference:
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "promoted snapshot source_url and evidence_reference are required",
        )

    events: list[ShareChangingCorporateAction] = []
    raw_events = payload.get("corporate_action_events") or []
    if not isinstance(raw_events, list):
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            "corporate_action_events must be a list",
        )
    for item in raw_events:
        if not isinstance(item, Mapping):
            raise ShareCountResolutionError(
                SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
                "corporate_action_events entries must be objects",
            )
        events.append(
            ShareChangingCorporateAction(
                action_type=str(item.get("action_type") or "").strip().lower(),
                effective_date=_parse_iso_date(
                    item.get("effective_date"), field="event.effective_date"
                )
                if item.get("effective_date") not in (None, "")
                else None,
                changes_outstanding_shares=item.get("changes_outstanding_shares"),
                already_reflected_in_share_count=item.get(
                    "already_reflected_in_share_count"
                ),
                description=(
                    str(item["description"]) if item.get("description") else None
                ),
            )
        )

    as_of_dt = datetime.combine(as_of, time.min, tzinfo=UTC)
    snapshot = ShareCountSnapshot(
        symbol=symbol,
        exchange=exchange,
        isin=isin,
        shares=ShareCountField.of(shares),
        basis=ShareCountBasis.CURRENT_OUTSTANDING,
        unit=ShareCountUnit.SHARES,
        as_of=as_of_dt,
        provenance=ShareCountProvenance(
            provider_id=str(source.get("provider_id") or _PROVIDER_ID),
            provider_name=str(
                source.get("provider_name") or "Promoted T1 share-count snapshot"
            ),
            source_type=str(source.get("source_type") or "primary_filing"),
            retrieved_at=as_of_dt,
            as_of=as_of_dt,
            auth_mode="promoted_snapshot",
            endpoint=source_url,
            metadata={
                "mic": mic,
                "as_of": as_of.isoformat(),
                "effective_date": effective.isoformat(),
                "complete_through": complete_through.isoformat(),
                "source_tier": source_tier,
                "corporate_action_adjusted": "true",
                "evidence_reference": evidence_reference,
                "integrity_sha256": expected,
            },
        ),
    )
    validate_share_count_snapshot(snapshot)
    return _PromotedRecord(
        snapshot=snapshot,
        as_of=as_of,
        complete_through=complete_through,
        source_tier=source_tier,
        source_url=source_url,
        evidence_reference=evidence_reference,
        events=tuple(events),
        mic=mic,
        shares=shares,
    )


def load_promoted_share_count_records(
    directory: Path,
) -> tuple[dict[str, _PromotedRecord], dict[str, str]]:
    """Load identity-keyed records. Values in ``blocked`` are fail-closed codes."""
    records: dict[str, _PromotedRecord] = {}
    blocked: dict[str, str] = {}
    if not directory.is_dir():
        return records, blocked
    for path in sorted(directory.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        try:
            record = _record_from_payload(payload)
        except ShareCountResolutionError as exc:
            identity = payload.get("identity")
            isin = _norm(identity.get("isin")) if isinstance(identity, Mapping) else ""
            if isin:
                blocked[isin] = exc.code
            continue
        isin = _norm(record.snapshot.isin)
        if isin in blocked:
            continue
        existing = records.get(isin)
        if existing is None:
            records[isin] = record
            continue
        if existing.shares != record.shares or existing.as_of != record.as_of:
            del records[isin]
            blocked[isin] = SHARES_OUTSTANDING_CONFLICT
    return records, blocked


class DurablePromotedShareCountAdapter(ShareCountPort):
    """Production ShareCountPort over durable validated snapshots."""

    def __init__(
        self,
        directory: Path | None = None,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._directory = directory or DEFAULT_PROMOTED_SHARE_COUNT_DIR
        self._now = now or horizon_now
        self._records, self._blocked = load_promoted_share_count_records(
            self._directory
        )

    @property
    def provider_id(self) -> str:
        return _PROVIDER_ID

    def health(self) -> ShareCountProviderHealth:
        return ShareCountProviderHealth(
            provider_id=self.provider_id,
            healthy=True,
            authenticated=True,
            detail=(
                f"promoted snapshots loaded={len(self._records)} "
                f"blocked={len(self._blocked)}"
            ),
        )

    def get_share_count(self, instrument: Instrument) -> ShareCountSnapshot | None:
        isin = _norm(instrument.isin)
        if not isin:
            return None
        blocked = self._blocked.get(isin)
        if blocked:
            raise ShareCountResolutionError(blocked, f"ISIN {isin}")
        record = self._records.get(isin)
        if record is None:
            return None
        self._assert_identity(instrument, record)
        self._assert_currentness(record)
        return record.snapshot

    def _assert_identity(self, instrument: Instrument, record: _PromotedRecord) -> None:
        requested_exchange = _norm(instrument.exchange)
        requested_mic = _EXCHANGE_TO_MIC.get(requested_exchange, "")
        equivalent_listing = bool(
            requested_mic and _mics_equivalent(requested_mic, record.mic)
        )
        if requested_mic and not equivalent_listing:
            raise ShareCountResolutionError(
                SHARES_OUTSTANDING_IDENTITY_MISMATCH,
                f"MIC {requested_mic} does not match snapshot {record.mic}",
            )
        # Same ISIN on NSE/BSE is one equity (XNSE ≡ XBOM). Venue strings
        # NSE vs BSE must not override that MIC contract.
        exchange_for_assert = None if equivalent_listing else instrument.exchange
        try:
            assert_share_count_identity(
                record.snapshot,
                symbol=instrument.symbol,
                exchange=exchange_for_assert,
                isin=instrument.isin,
            )
        except Exception as exc:
            raise ShareCountResolutionError(
                SHARES_OUTSTANDING_IDENTITY_MISMATCH,
                str(exc),
            ) from exc

    def _assert_currentness(self, record: _PromotedRecord) -> None:
        retrieved_at = self._now()
        if retrieved_at.tzinfo is None:
            raise ShareCountResolutionError(
                SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
                "lookup horizon must be timezone-aware",
            )
        evidence = CorporateActionCurrentnessEvidence(
            events=record.events,
            complete_through=record.complete_through,
            share_count_as_of=record.as_of,
            source_tier=record.source_tier,
            source_url=record.source_url,
            evidence_reference=record.evidence_reference,
        )
        verdict = evaluate_option_b_currentness(
            share_count_as_of=record.as_of,
            retrieved_at=retrieved_at,
            evidence=evidence,
        )
        if verdict.proven:
            return
        reason = verdict.reason or "Option B currentness is unproven"
        if "does not reach retrieved_at" in reason or "complete_through" in reason:
            raise ShareCountResolutionError(SHARES_OUTSTANDING_STALE, reason)
        raise ShareCountResolutionError(
            SHARES_OUTSTANDING_CURRENTNESS_UNPROVEN,
            reason,
        )
