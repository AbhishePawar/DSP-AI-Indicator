"""Citation helpers for Investment Policy (EPIC-A006)."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.investment_policy.models import UNAVAILABLE_MESSAGE, freeze_mapping

__all__ = ["build_policy_citations", "citation"]


def citation(
    *,
    source_kind: str,
    section: str,
    path: str,
    available: bool,
    rule_id: str | None = None,
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
    if rule_id:
        row["rule_id"] = rule_id
    if symbol:
        row["symbol"] = symbol
    if ref_id:
        row["ref_id"] = ref_id
    if not available:
        row["message"] = UNAVAILABLE_MESSAGE
    return freeze_mapping(row) or freeze_mapping({})


def build_policy_citations(
    rule_citations: list[Mapping[str, Any]],
) -> tuple[Mapping[str, Any], ...]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[Mapping[str, Any]] = []
    for c in rule_citations:
        key = (
            str(c.get("rule_id") or ""),
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
            str(c.get("rule_id") or ""),
            str(c.get("source_kind") or ""),
            str(c.get("section") or ""),
            str(c.get("path") or ""),
        )
    )
    return tuple(out)
