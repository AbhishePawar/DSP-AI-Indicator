"""Human-gated promotion of a VALIDATED share-count refresh candidate.

Does not fetch vendors, call Gemini, or extend complete_through.
Refresh never writes production files; this module writes only after
explicit human approval and Option-B/source gates.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from dsp_platform.promoted_share_count import (
    canonical_promoted_snapshot_digest,
    sign_promoted_snapshot,
)
from dsp_platform.share_count_refresh import (
    CoverageState,
    ShareCountRefreshResult,
)
from dsp_platform.share_count_source_authorization import (
    SourceRole,
    assert_source_authorized,
)

__all__ = [
    "ShareCountPromotionError",
    "ShareCountPromotionRecord",
    "promote_validated_candidate",
]

_FORBIDDEN = frozenset(
    {
        "float",
        "free_float",
        "free_float_shares",
        "float_shares",
        "weighted_average",
        "weighted_average_shares",
        "market_cap_implied_shares",
        "implied_shares",
    }
)


class ShareCountPromotionError(Exception):
    """Fail-closed promotion. Does not write on error."""


@dataclass(frozen=True, slots=True)
class ShareCountPromotionRecord:
    promoted: bool
    path: Path | None
    previous_path: Path | None
    integrity: str | None
    previous_integrity: str | None
    promoted_at: datetime
    reason: str
    filename: str | None = None


def promote_validated_candidate(
    result: ShareCountRefreshResult,
    *,
    destination_dir: Path,
    history_dir: Path,
    human_approved: bool,
    lookup_horizon: datetime,
    promoter: str,
) -> ShareCountPromotionRecord:
    """Sign and write a VALIDATED candidate. Never auto-promotes."""
    assert_source_authorized("manual_promotion", SourceRole.PROMOTION)
    now = datetime.now(tz=UTC)
    if not human_approved:
        raise ShareCountPromotionError(
            "human approval is required; refresh cannot auto-promote"
        )
    if not str(promoter or "").strip():
        raise ShareCountPromotionError("promoter identity is required")
    if not isinstance(lookup_horizon, datetime) or lookup_horizon.tzinfo is None:
        raise ShareCountPromotionError(
            "lookup_horizon must be timezone-aware and is not as_of"
        )
    if result.state is CoverageState.CURRENT:
        raise ShareCountPromotionError(
            "existing snapshot remains current; no new artifact to promote"
        )
    if result.state is CoverageState.STALE:
        raise ShareCountPromotionError(
            "stale candidate cannot be promoted; Option B is unproven at horizon"
        )
    if result.state is not CoverageState.VALIDATED or result.candidate is None:
        raise ShareCountPromotionError(
            f"only VALIDATED candidates may be promoted; state={result.state}"
        )
    if result.source_status is not None and str(result.source_status) != "APPROVED":
        raise ShareCountPromotionError("PENDING/REJECTED sources cannot promote")

    candidate = dict(result.candidate)
    refresh_meta = candidate.pop("refresh", None)
    if not isinstance(refresh_meta, dict) or refresh_meta.get(
        "human_promotion_required"
    ) is not True:
        raise ShareCountPromotionError(
            "candidate is missing human_promotion_required=true"
        )
    _assert_promotable_payload(candidate, lookup_horizon=lookup_horizon.date())
    if result.complete_through != _parse_date(candidate.get("complete_through")):
        raise ShareCountPromotionError(
            "candidate complete_through does not match refresh result"
        )

    identity = candidate["identity"]
    filename = f"{identity['isin']}_{identity['mic']}.json"
    destination_dir = Path(destination_dir)
    history_dir = Path(history_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    history_dir.mkdir(parents=True, exist_ok=True)
    dest = destination_dir / filename

    previous_path: Path | None = None
    previous_integrity: str | None = None
    if dest.exists():
        previous = json.loads(dest.read_text(encoding="utf-8"))
        previous_integrity = str(
            (previous.get("integrity") or {}).get("sha256") or ""
        ) or None
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        previous_path = history_dir / f"{stamp}_{filename}"
        shutil.copy2(dest, previous_path)

    signed = sign_promoted_snapshot(candidate)
    digest = str(signed["integrity"]["sha256"])
    if previous_integrity == digest:
        raise ShareCountPromotionError(
            "candidate is identical to the existing snapshot; refusing no-op overwrite"
        )
    dest.write_text(json.dumps(signed, indent=2) + "\n", encoding="utf-8")
    meta = {
        "promoted_at": now.isoformat(),
        "promoter": promoter,
        "filename": filename,
        "integrity": digest,
        "previous_integrity": previous_integrity,
        "lookup_horizon": lookup_horizon.isoformat(),
        "complete_through": candidate.get("complete_through"),
        "as_of": candidate.get("as_of"),
        "shares_outstanding": candidate.get("shares_outstanding"),
        "human_approved": True,
    }
    (history_dir / f"{now.strftime('%Y%m%dT%H%M%SZ')}_{filename}.promotion.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    return ShareCountPromotionRecord(
        promoted=True,
        path=dest,
        previous_path=previous_path,
        integrity=digest,
        previous_integrity=previous_integrity,
        promoted_at=now,
        reason="human-approved VALIDATED candidate signed and written",
        filename=filename,
    )


def _assert_promotable_payload(payload: dict[str, Any], *, lookup_horizon: date) -> None:
    keys = {str(key).strip().lower() for key in payload}
    if keys & _FORBIDDEN:
        raise ShareCountPromotionError(
            "float/WAS/implied share fields cannot be promoted"
        )
    identity = payload.get("identity")
    if not isinstance(identity, dict):
        raise ShareCountPromotionError("candidate identity is required")
    for field in ("symbol", "exchange", "mic", "isin"):
        if not str(identity.get(field) or "").strip():
            raise ShareCountPromotionError(f"candidate identity.{field} is required")
    if payload.get("basis") != "current_outstanding":
        raise ShareCountPromotionError("only current_outstanding may be promoted")
    if payload.get("unit") != "shares":
        raise ShareCountPromotionError("promoted unit must be shares")
    if payload.get("corporate_action_adjusted") is not True:
        raise ShareCountPromotionError("candidate must be corporate-action adjusted")
    as_of = _parse_date(payload.get("as_of"))
    effective = _parse_date(payload.get("effective_date") or payload.get("as_of"))
    complete = _parse_date(payload.get("complete_through"))
    if as_of is None or effective is None or complete is None:
        raise ShareCountPromotionError("as_of, effective_date, and complete_through are required")
    if complete > lookup_horizon:
        raise ShareCountPromotionError(
            "complete_through cannot exceed the attested lookup horizon"
        )
    if complete < as_of:
        raise ShareCountPromotionError("complete_through is before as_of")
    if as_of > lookup_horizon:
        raise ShareCountPromotionError("as_of is after lookup horizon")
    source = payload.get("source")
    if not isinstance(source, dict) or not source.get("source_url") or not source.get(
        "evidence_reference"
    ):
        raise ShareCountPromotionError("candidate source_url and evidence_reference are required")
    if "outstanding" not in str(source.get("evidence_reference") or "").lower():
        raise ShareCountPromotionError(
            "evidence_reference does not explicitly support outstanding shares"
        )
    canonical_promoted_snapshot_digest(payload)


def _parse_date(raw: object) -> date | None:
    if isinstance(raw, datetime):
        return None
    if isinstance(raw, date):
        return raw
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None
