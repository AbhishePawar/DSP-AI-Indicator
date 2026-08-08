"""Research timeline builder (EPIC-A004) — aggregates timestamps only."""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.decision_workspace.models import (
    UNAVAILABLE_MESSAGE,
    TimelineEvent,
    freeze_mapping,
)

__all__ = ["build_research_timeline"]


def _ts(value: Any, fallback: str = "") -> str:
    return str(value or fallback or "")


def build_research_timeline(
    *,
    research_object: Mapping[str, Any] | None = None,
    report: Mapping[str, Any] | None = None,
    snapshots: list[Mapping[str, Any]] | None = None,
    diffs: list[Mapping[str, Any]] | None = None,
    monitoring_result: Mapping[str, Any] | None = None,
    created_at: str = "",
) -> tuple[TimelineEvent, ...]:
    events: list[TimelineEvent] = []

    if research_object is not None:
        rid = str(
            research_object.get("object_id")
            or research_object.get("research_object_id")
            or "research_object"
        )
        events.append(
            TimelineEvent(
                event_id=f"tl-ro-{rid}",
                event_type="research_object",
                timestamp=_ts(
                    research_object.get("created_at")
                    or research_object.get("generated_at"),
                    created_at,
                ),
                label="Research Object available",
                source_kind="research_object",
                available=True,
                ref_id=rid,
                metadata=freeze_mapping(
                    {"symbol": research_object.get("symbol")}
                )
                or freeze_mapping({}),
            )
        )

    if report is not None:
        rid = str(report.get("report_id") or "report")
        events.append(
            TimelineEvent(
                event_id=f"tl-rpt-{rid}",
                event_type="institutional_report",
                timestamp=_ts(
                    report.get("generated_at") or report.get("created_at"),
                    created_at,
                ),
                label="Institutional Report available",
                source_kind="institutional_report",
                available=True,
                ref_id=rid,
                metadata=freeze_mapping({}) or freeze_mapping({}),
            )
        )

    for idx, snap in enumerate(snapshots or []):
        if not isinstance(snap, Mapping):
            continue
        sid = str(snap.get("snapshot_id") or f"snapshot-{idx}")
        version = (
            snap.get("version") if isinstance(snap.get("version"), Mapping) else {}
        )
        archived = _ts(
            snap.get("archived_at") or version.get("created_at"),
            created_at,
        )
        events.append(
            TimelineEvent(
                event_id=f"tl-snap-{sid}",
                event_type="archive_snapshot",
                timestamp=archived,
                label=f"Archive snapshot {sid}",
                source_kind="research_archive",
                available=True,
                ref_id=sid,
                metadata=freeze_mapping(
                    {
                        "kind": snap.get("kind"),
                        "lineage_id": version.get("lineage_id"),
                    }
                )
                or freeze_mapping({}),
            )
        )

    for idx, diff in enumerate(diffs or []):
        if not isinstance(diff, Mapping):
            continue
        did = str(diff.get("diff_id") or f"diff-{idx}")
        summary = (
            diff.get("change_summary")
            if isinstance(diff.get("change_summary"), Mapping)
            else {}
        )
        events.append(
            TimelineEvent(
                event_id=f"tl-diff-{did}",
                event_type="research_diff",
                timestamp=_ts(diff.get("created_at"), created_at),
                label=f"Research diff {did}",
                source_kind="research_diff",
                available=True,
                ref_id=did,
                metadata=freeze_mapping(
                    {"identical_content": summary.get("identical_content")}
                )
                or freeze_mapping({}),
            )
        )

    if monitoring_result is not None:
        mid = str(monitoring_result.get("result_id") or "monitoring")
        events.append(
            TimelineEvent(
                event_id=f"tl-mon-{mid}",
                event_type="monitoring_evaluate",
                timestamp=_ts(monitoring_result.get("created_at"), created_at),
                label="Monitoring evaluation",
                source_kind="research_monitoring",
                available=True,
                ref_id=mid,
                metadata=freeze_mapping(
                    {
                        "alert_count": len(
                            monitoring_result.get("alerts") or []
                        )
                    }
                )
                or freeze_mapping({}),
            )
        )

    if not events:
        events.append(
            TimelineEvent(
                event_id="tl-unavailable",
                event_type="unavailable",
                timestamp=created_at,
                label="Timeline",
                source_kind="decision_workspace",
                available=False,
                message=UNAVAILABLE_MESSAGE,
                metadata=freeze_mapping({}) or freeze_mapping({}),
            )
        )

    events.sort(key=lambda e: (e.timestamp, e.event_type, e.event_id))
    return tuple(events)
