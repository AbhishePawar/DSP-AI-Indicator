"""Citation helpers for Decision Workspace (EPIC-A004)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.decision_workspace.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = [
    "build_workspace_citations",
    "citation",
]


def citation(
    *,
    source_kind: str,
    section: str,
    path: str,
    available: bool,
    label: str | None = None,
    symbol: str | None = None,
    ref_id: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    row: dict[str, Any] = {
        "source_kind": source_kind,
        "section": section,
        "path": path,
        "available": available,
        "label": label or f"{source_kind}/{section}",
    }
    if symbol is not None:
        row["symbol"] = symbol
    if ref_id is not None:
        row["ref_id"] = ref_id
    if not available:
        row["message"] = UNAVAILABLE_MESSAGE
    if extra:
        row.update(dict(extra))
    return freeze_mapping(row) or freeze_mapping({})


def build_workspace_citations(
    panel_citations: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    """Deduplicate and sort workspace-level citations."""
    seen: set[tuple[str, str, str]] = set()
    out: list[Mapping[str, Any]] = []
    for c in panel_citations:
        key = (
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
            str(c.get("source_kind") or ""),
            str(c.get("section") or ""),
            str(c.get("path") or ""),
        )
    )
    return tuple(out)
