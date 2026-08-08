"""Structural walk for research diffs (EPIC-R005) — equality only."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_archive.hashing import to_plain_jsonable
from dsp_platform.research_diff.models import FieldDiff, UNAVAILABLE_MESSAGE

__all__ = [
    "EXPORT_DIFF_SECTIONS",
    "MISSING",
    "REPORT_DIFF_SECTIONS",
    "RESEARCH_OBJECT_DIFF_SECTIONS",
    "compare_values",
    "diff_mapping",
    "section_payload",
]

MISSING = object()

# Deterministic section order aligned to R001 / R002 contracts
RESEARCH_OBJECT_DIFF_SECTIONS = (
    "metadata",
    "identity",
    "market_data",
    "financial_statements",
    "corporate_actions",
    "historical_series",
    "valuation",
    "margin_of_safety",
    "business_quality",
    "risk",
    "scenarios",
    "recommendation",
    "explainability",
    "audit",
    "provenance",
    "version",
    "data_retrieval",
    "data_health",
)

REPORT_DIFF_SECTIONS = (
    "metadata",
    "header",
    "executive_summary",
    "market_data",
    "financial_statements",
    "corporate_actions",
    "historical_summary",
    "valuation",
    "margin_of_safety",
    "business_quality",
    "risk",
    "scenarios",
    "recommendation",
    "explainability",
    "audit",
    "provenance",
    "version",
    "research_object_ref",
)

EXPORT_DIFF_SECTIONS = (
    "metadata",
    "version",
    "content_base64",
    "content_sha256",
    "content_text",
    "structured_json",
)


def compare_values(left: Any, right: Any) -> str:
    """Return diff status for two plain values — no interpretation."""
    if left is MISSING and right is MISSING:
        return "unchanged"
    if left is MISSING:
        return "added"
    if right is MISSING:
        return "removed"
    if left == right:
        return "unchanged"
    return "changed"


def diff_mapping(
    left: Any,
    right: Any,
    *,
    prefix: str = "",
) -> tuple[FieldDiff, ...]:
    """Deep structural equality walk. Deterministic path order."""
    left_p = to_plain_jsonable(left) if left is not MISSING else MISSING
    right_p = to_plain_jsonable(right) if right is not MISSING else MISSING

    if isinstance(left_p, dict) and isinstance(right_p, dict):
        keys = sorted(set(left_p.keys()) | set(right_p.keys()), key=str)
        out: list[FieldDiff] = []
        for key in keys:
            path = f"{prefix}.{key}" if prefix else str(key)
            l_val = left_p[key] if key in left_p else MISSING
            r_val = right_p[key] if key in right_p else MISSING
            if isinstance(l_val, dict) and isinstance(r_val, dict):
                out.extend(diff_mapping(l_val, r_val, prefix=path))
            elif isinstance(l_val, list) and isinstance(r_val, list):
                out.extend(_diff_lists(l_val, r_val, path))
            else:
                status = compare_values(l_val, r_val)
                out.append(
                    FieldDiff(
                        path=path,
                        status=status,
                        left_value=_display(l_val),
                        right_value=_display(r_val),
                    )
                )
        return tuple(out)

    if isinstance(left_p, list) and isinstance(right_p, list):
        return _diff_lists(left_p, right_p, prefix or "root")

    status = compare_values(left_p, right_p)
    return (
        FieldDiff(
            path=prefix or "root",
            status=status,
            left_value=_display(left_p),
            right_value=_display(right_p),
        ),
    )


def _diff_lists(left: list[Any], right: list[Any], prefix: str) -> tuple[FieldDiff, ...]:
    """Index-aligned list comparison only — no analytics."""
    n = max(len(left), len(right))
    out: list[FieldDiff] = []
    for i in range(n):
        path = f"{prefix}[{i}]"
        l_val = left[i] if i < len(left) else MISSING
        r_val = right[i] if i < len(right) else MISSING
        if isinstance(l_val, dict) and isinstance(r_val, dict):
            out.extend(diff_mapping(l_val, r_val, prefix=path))
        else:
            status = compare_values(l_val, r_val)
            out.append(
                FieldDiff(
                    path=path,
                    status=status,
                    left_value=_display(l_val),
                    right_value=_display(r_val),
                )
            )
    return tuple(out)


def _display(value: Any) -> Any:
    if value is MISSING:
        return UNAVAILABLE_MESSAGE
    return value


def section_payload(payload: Mapping[str, Any], name: str) -> Any:
    if name not in payload:
        return MISSING
    return payload.get(name)
