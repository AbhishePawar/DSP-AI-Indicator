"""Citation builder (EPIC-A001)."""

from __future__ import annotations

from dsp_platform.research_copilot.models import Citation, ResearchContextBundle

__all__ = ["build_citations"]


def build_citations(
    context: ResearchContextBundle,
    *,
    sections: list[tuple[str, str, bool]],
) -> tuple[Citation, ...]:
    """Build citations for (source_kind, section, available) triples."""
    refs = dict(context.source_refs)
    citations: list[Citation] = []
    for source_kind, section, available in sections:
        citations.append(
            Citation(
                source_kind=source_kind,
                section=section,
                path=f"{source_kind}.{section}",
                available=available,
                label=f"{source_kind}/{section}",
                research_object_id=refs.get("research_object_id")
                or refs.get("report_research_object_id"),
                report_id=refs.get("report_id"),
                snapshot_id=refs.get("snapshot_id"),
                diff_id=refs.get("diff_id"),
            )
        )
    citations.sort(key=lambda c: (c.source_kind, c.section, c.path))
    return tuple(citations)
