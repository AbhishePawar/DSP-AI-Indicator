"""Ingest official exchange documents into a versioned Security Master snapshot."""

from __future__ import annotations

from typing import Any

from dsp_platform.security_master.http import fetch_official_documents
from dsp_platform.security_master.models import SourceDocument, UniverseSnapshot
from dsp_platform.security_master.snapshot import build_snapshot
from dsp_platform.security_master.store import get_security_master_store

__all__ = ["ingest_documents", "ingest_official_universe"]


def ingest_documents(
    documents: tuple[SourceDocument, ...] | list[SourceDocument],
    *,
    store: Any | None = None,
    enforce_minimums: bool = False,
) -> UniverseSnapshot:
    snapshot = build_snapshot(tuple(documents), enforce_minimums=enforce_minimums)
    target = store if store is not None else get_security_master_store()
    return target.save_snapshot(snapshot)


def ingest_official_universe(*, store: Any | None = None, http: Any | None = None) -> UniverseSnapshot:
    documents = fetch_official_documents(http)
    return ingest_documents(documents, store=store, enforce_minimums=True)
