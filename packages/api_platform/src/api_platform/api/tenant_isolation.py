"""P1-07 helpers — owner-scoped report access (server identity only)."""

from __future__ import annotations

from typing import Any


def stamp_report_owner(payload: dict[str, Any], owner_user_id: str) -> dict[str, Any]:
    """Attach authoritative owner metadata; strip any client-supplied owner."""
    data = dict(payload)
    data.pop("owner_user_id", None)
    data["owner_user_id"] = str(owner_user_id).strip()
    return data


def report_owner_id(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    owner = str(record.get("owner_user_id") or "").strip()
    return owner or None


def actor_owns_report(record: Any, actor_user_id: str) -> bool:
    owner = report_owner_id(record)
    actor = str(actor_user_id or "").strip()
    return bool(owner and actor and owner == actor)
