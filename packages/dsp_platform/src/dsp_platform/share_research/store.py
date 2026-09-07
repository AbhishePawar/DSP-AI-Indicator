"""Share-research store. History is never silently overwritten.

FilesystemShareResearchStore is the test/dev default. Production API boot
wires DatabaseShareResearchStore via DatabasePort (Cloud SQL).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import Any

from dsp_platform.share_research.models import (
    ShareResearchCheck,
    ShareResearchCorporateAction,
    ShareResearchRecord,
    ShareResearchSource,
    ShareResearchStatus,
)

__all__ = [
    "DEFAULT_SHARE_RESEARCH_DIR",
    "ShareResearchStore",
    "configure_share_research_store",
    "get_share_research_store",
    "record_from_dict",
    "reset_share_research_store_for_tests",
]

DEFAULT_SHARE_RESEARCH_DIR = (
    Path(__file__).resolve().parent.parent / "share_research_store"
)


class ShareResearchStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root is not None else DEFAULT_SHARE_RESEARCH_DIR
        self.current_dir = self.root / "current"
        self.history_dir = self.root / "history"
        self.current_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _current_path(self, isin: str) -> Path:
        return self.current_dir / f"{isin.strip().upper()}.json"

    def load_current(self, isin: str) -> ShareResearchRecord | None:
        path = self._current_path(isin)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        return record_from_dict(payload)

    def load_history(self, isin: str, *, limit: int = 20) -> tuple[dict[str, Any], ...]:
        folder = self.history_dir / isin.strip().upper()
        if not folder.is_dir():
            return ()
        files = sorted(folder.glob("*.json"), reverse=True)
        rows: list[dict[str, Any]] = []
        for path in files[:limit]:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict):
                rows.append(
                    {
                        "research_id": payload.get("research_id"),
                        "status": payload.get("status"),
                        "outstanding_shares": payload.get("outstanding_shares"),
                        "as_of": payload.get("as_of"),
                        "current_through": payload.get("current_through"),
                        "last_verified_at": payload.get("last_verified_at"),
                        "researched_at": payload.get("researched_at"),
                    }
                )
        return tuple(rows)

    def save(self, record: ShareResearchRecord) -> None:
        previous = self.load_current(record.isin)
        if previous is not None:
            hist = self.history_dir / record.isin
            hist.mkdir(parents=True, exist_ok=True)
            name = f"{previous.researched_at.strftime('%Y%m%dT%H%M%SZ')}_{previous.research_id}.json"
            (hist / name).write_text(
                json.dumps(previous.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
        path = self._current_path(record.isin)
        path.write_text(json.dumps(record.to_dict(), indent=2) + "\n", encoding="utf-8")


def record_from_dict(payload: dict[str, Any]) -> ShareResearchRecord | None:
    try:
        status = ShareResearchStatus(str(payload.get("status") or "UNKNOWN"))
    except ValueError:
        return None
    sources = tuple(
        ShareResearchSource(
            url=str(row.get("url") or ""),
            label=str(row.get("label") or ""),
            accepted=bool(row.get("accepted")),
            reason=str(row.get("reason") or ""),
        )
        for row in (payload.get("primary_sources") or [])
        if isinstance(row, dict)
    )
    actions = tuple(
        ShareResearchCorporateAction(
            action_type=str(row.get("action_type") or ""),
            description=str(row.get("description") or ""),
            effective_date=_parse_date(row.get("effective_date")),
            changes_outstanding_shares=row.get("changes_outstanding_shares")
            if isinstance(row.get("changes_outstanding_shares"), bool)
            else None,
            consideration=str(row.get("consideration") or "") or None,
        )
        for row in (payload.get("corporate_actions") or [])
        if isinstance(row, dict)
    )
    researched = _parse_dt(payload.get("researched_at"))
    verified = _parse_dt(payload.get("last_verified_at")) or researched
    created = _parse_dt(payload.get("created_at")) or researched
    updated = _parse_dt(payload.get("updated_at")) or verified
    if researched is None or verified is None:
        return None
    return ShareResearchRecord(
        research_id=str(payload.get("research_id") or ""),
        company_name=str(payload.get("company_name") or ""),
        ticker=str(payload.get("ticker") or ""),
        isin=str(payload.get("isin") or ""),
        exchange=str(payload.get("exchange") or ""),
        mic=str(payload.get("mic") or ""),
        security_type=str(payload.get("security_type") or "common_equity"),
        outstanding_shares=_parse_decimal(payload.get("outstanding_shares")),
        as_of=_parse_date(payload.get("as_of")),
        effective_date=_parse_date(payload.get("effective_date")),
        current_through=_parse_date(payload.get("current_through")),
        researched_at=researched,
        last_verified_at=verified,
        status=status,
        stored_previous_share_count=_parse_decimal(
            payload.get("stored_previous_share_count")
        ),
        stored_previous_as_of=_parse_date(payload.get("stored_previous_as_of")),
        stored_previous_current_through=_parse_date(
            payload.get("stored_previous_current_through")
        ),
        primary_sources=sources,
        evidence=tuple(str(item) for item in (payload.get("evidence") or [])),
        corporate_actions=actions,
        share_count_effect=str(payload.get("share_count_effect") or ""),
        identity_check=_check(payload.get("identity_check")),
        cross_check=_check(payload.get("cross_check")),
        corporate_action_check=_check(payload.get("corporate_action_check")),
        confidence=str(payload.get("confidence") or "LOW"),
        gemini_invoked=bool(payload.get("gemini_invoked")),
        gemini_research_reference=str(payload.get("gemini_research_reference") or ""),
        integrity_hash=str(payload.get("integrity_hash") or ""),
        valuation_eligible=bool(payload.get("valuation_eligible")),
        unresolved_issues=tuple(
            str(item) for item in (payload.get("unresolved_issues") or [])
        ),
        created_at=created,
        updated_at=updated,
        reason=str(payload.get("reason") or ""),
        gemini_duration_ms=(
            int(payload["gemini_duration_ms"])
            if isinstance(payload.get("gemini_duration_ms"), int)
            else None
        ),
        stored_record_status=str(payload.get("stored_record_status") or ""),
        promotion_recommended=bool(payload.get("promotion_recommended")),
    )


def _check(raw: object) -> ShareResearchCheck:
    try:
        return ShareResearchCheck(str(raw or "NOT_RUN"))
    except ValueError:
        return ShareResearchCheck.NOT_RUN


def _parse_date(raw: object) -> date | None:
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_dt(raw: object) -> datetime | None:
    if isinstance(raw, datetime):
        return raw
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_decimal(raw: object) -> Decimal | None:
    if raw is None or raw == "":
        return None
    try:
        value = Decimal(str(raw))
    except Exception:  # noqa: BLE001
        return None
    if not value.is_finite():
        return None
    return value


_STORE: Any | None = None
_STORE_LOCK = Lock()


def configure_share_research_store(database: Any | None = None) -> Any:
    """Wire DatabasePort-backed store when shared SQL primitives exist."""
    global _STORE
    with _STORE_LOCK:
        if database is not None and all(
            hasattr(database, name) for name in ("execute", "fetchall", "ping")
        ):
            from dsp_platform.share_research.db_store import DatabaseShareResearchStore

            _STORE = DatabaseShareResearchStore(database)
        else:
            _STORE = ShareResearchStore()
        return _STORE


def get_share_research_store() -> Any:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = ShareResearchStore()
        return _STORE


def reset_share_research_store_for_tests(store: Any | None = None) -> Any:
    global _STORE
    with _STORE_LOCK:
        _STORE = store
        return _STORE
