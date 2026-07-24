"""Deterministic filtering and grouping for universe membership.

Uses only explicit Instrument metadata and user-supplied tags.
Never infers sector/industry from names.
"""

from __future__ import annotations

from collections import defaultdict

from contracts import AssetClass

from universe.models import InvestmentUniverse, UniverseEntry

__all__ = ["filter_entries", "group_entries"]


def filter_entries(
    universe: InvestmentUniverse,
    *,
    sector: str | None = None,
    industry: str | None = None,
    asset_class: AssetClass | None = None,
    tag: str | None = None,
    tags_all: frozenset[str] | set[str] | None = None,
) -> tuple[UniverseEntry, ...]:
    """Return matching entries in the universe's deterministic order."""
    sector_key = sector.strip().lower() if sector else None
    industry_key = industry.strip().lower() if industry else None
    tag_key = tag.strip().lower() if tag else None
    required_tags = (
        frozenset(t.strip().lower() for t in tags_all if t.strip())
        if tags_all
        else None
    )

    selected: list[UniverseEntry] = []
    for entry in universe.entries():
        inst = entry.instrument
        if sector_key is not None:
            if (inst.sector or "").strip().lower() != sector_key:
                continue
        if industry_key is not None:
            if (inst.industry or "").strip().lower() != industry_key:
                continue
        if asset_class is not None and inst.asset_class is not asset_class:
            continue
        if tag_key is not None and tag_key not in entry.tags:
            continue
        if required_tags is not None and not required_tags.issubset(entry.tags):
            continue
        selected.append(entry)
    return tuple(selected)


def group_entries(
    universe: InvestmentUniverse,
    *,
    by: str,
) -> dict[str, tuple[UniverseEntry, ...]]:
    """Group entries by an explicit metadata key.

    Supported keys: ``sector``, ``industry``, ``asset_class``, ``tag``.
    Unknown/missing metadata maps to ``\"unspecified\"``.
    For ``tag``, an entry appears under each of its tags (multi-membership).
    Entries with no tags appear under ``unspecified``.
    """
    key = by.strip().lower()
    if key not in {"sector", "industry", "asset_class", "tag"}:
        msg = f"unsupported group key: {by!r}"
        raise ValueError(msg)

    buckets: dict[str, list[UniverseEntry]] = defaultdict(list)
    for entry in universe.entries():
        inst = entry.instrument
        if key == "sector":
            label = (inst.sector or "").strip() or "unspecified"
            buckets[label.lower()].append(entry)
        elif key == "industry":
            label = (inst.industry or "").strip() or "unspecified"
            buckets[label.lower()].append(entry)
        elif key == "asset_class":
            buckets[inst.asset_class.value].append(entry)
        else:  # tag
            if not entry.tags:
                buckets["unspecified"].append(entry)
            else:
                for tag in sorted(entry.tags):
                    buckets[tag].append(entry)

    return {
        label: tuple(items)
        for label, items in sorted(buckets.items(), key=lambda kv: kv[0])
    }
