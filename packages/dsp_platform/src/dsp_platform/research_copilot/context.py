"""Context builder (EPIC-A001) — assemble R001/R002/R004/R005 read-only."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_archive.hashing import to_plain_jsonable
from dsp_platform.research_copilot.models import ResearchContextBundle, freeze_mapping, utc_now

__all__ = ["build_research_context"]


def build_research_context(
    *,
    research_object: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
    archive_snapshot: Mapping[str, Any] | None = None,
    research_diff: Mapping[str, Any] | None = None,
    snapshot_id: str | None = None,
    assembled_at: str | None = None,
) -> ResearchContextBundle:
    """Build deterministic context. Optionally load archive snapshot by id."""
    snapshot = archive_snapshot
    if snapshot is None and snapshot_id:
        from dsp_platform.research_archive import get_research_archive

        snapshot = get_research_archive().get_dict(snapshot_id)

    ro = to_plain_jsonable(research_object) if research_object is not None else None
    rp = to_plain_jsonable(report) if report is not None else None
    sn = to_plain_jsonable(snapshot) if snapshot is not None else None
    df = to_plain_jsonable(research_diff) if research_diff is not None else None

    # If snapshot holds RO/report payload and dedicated inputs omitted, expose via refs only
    # — do not invent; consumers read snapshot.payload explicitly.
    refs: dict[str, Any] = {}
    if isinstance(ro, dict):
        meta = ro.get("metadata") if isinstance(ro.get("metadata"), dict) else {}
        refs["research_object_id"] = meta.get("research_object_id")
    if isinstance(rp, dict):
        meta = rp.get("metadata") if isinstance(rp.get("metadata"), dict) else {}
        refs["report_id"] = meta.get("report_id")
        refs["report_research_object_id"] = meta.get("research_object_id")
    if isinstance(sn, dict):
        refs["snapshot_id"] = sn.get("snapshot_id")
        refs["snapshot_kind"] = sn.get("kind")
        refs["snapshot_content_sha256"] = sn.get("content_sha256")
    if isinstance(df, dict):
        refs["diff_id"] = df.get("diff_id")
        refs["diff_left_snapshot_id"] = df.get("left_snapshot_id")
        refs["diff_right_snapshot_id"] = df.get("right_snapshot_id")

    return ResearchContextBundle(
        research_object=freeze_mapping(ro) if isinstance(ro, dict) else None,
        report=freeze_mapping(rp) if isinstance(rp, dict) else None,
        archive_snapshot=freeze_mapping(sn) if isinstance(sn, dict) else None,
        research_diff=freeze_mapping(df) if isinstance(df, dict) else None,
        assembled_at=assembled_at or utc_now().isoformat(),
        source_refs=freeze_mapping(refs) or freeze_mapping({}),
    )
