"""Citation helpers for Institutional Committee (EPIC-A005)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.institutional_committee.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = ["build_committee_citations", "citation"]


def citation(
    *,
    source_kind: str,
    section: str,
    path: str,
    available: bool,
    agent_id: str | None = None,
    label: str | None = None,
    symbol: str | None = None,
    ref_id: str | None = None,
) -> Mapping[str, Any]:
    row: dict[str, Any] = {
        "source_kind": source_kind,
        "section": section,
        "path": path,
        "available": available,
        "label": label or f"{source_kind}/{section}",
    }
    if agent_id:
        row["agent_id"] = agent_id
    if symbol:
        row["symbol"] = symbol
    if ref_id:
        row["ref_id"] = ref_id
    if not available:
        row["message"] = UNAVAILABLE_MESSAGE
    return freeze_mapping(row) or freeze_mapping({})


def build_committee_citations(
    reviews_citations: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[Mapping[str, Any]] = []
    for c in reviews_citations:
        key = (
            str(c.get("agent_id") or ""),
            str(c.get("source_kind") or ""),
            str(c.get("section") or ""),
            str(c.get("path") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    out.sort(
        key=lambda c: (
            str(c.get("agent_id") or ""),
            str(c.get("source_kind") or ""),
            str(c.get("section") or ""),
            str(c.get("path") or ""),
        )
    )
    return tuple(out)
