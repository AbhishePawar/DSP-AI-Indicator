"""Watchlist helpers (EPIC-A010)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from workspace.models import Watchlist, freeze_mapping, utc_now
from workspace.validation import assert_non_empty, normalize_companies

__all__ = ["build_watchlist"]


def build_watchlist(
    *,
    workspace_id: str,
    name: str,
    companies: list[str] | None = None,
    kind: str = "custom",
    sector: str | None = None,
    notes: str | None = None,
    order: list[str] | None = None,
    watchlist_id: str | None = None,
    created_at: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Watchlist:
    created = created_at or utc_now().isoformat()
    companies_t = normalize_companies(companies)
    order_t = normalize_companies(order) if order else companies_t
    return Watchlist(
        watchlist_id=watchlist_id or str(uuid.uuid4()),
        workspace_id=assert_non_empty(workspace_id, "workspace_id"),
        name=assert_non_empty(name, "watchlist name"),
        kind=str(kind or "custom").strip().lower(),
        companies=companies_t,
        sector=sector,
        notes=notes,
        order=order_t,
        created_at=created,
        updated_at=created,
        metadata=freeze_mapping(dict(metadata or {})),
    )
