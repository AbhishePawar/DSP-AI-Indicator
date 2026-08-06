"""Alert construction from R005 diffs / A002 summaries (EPIC-A003)."""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from dsp_platform.research_monitoring.models import (
    UNAVAILABLE_MESSAGE,
    MonitoringAlert,
    freeze_mapping,
)

__all__ = [
    "IMPORTANT_SECTIONS",
    "alerts_from_diff",
    "alerts_from_portfolio_intelligence",
    "severity_from_diff",
]

IMPORTANT_SECTIONS = frozenset(
    {
        "valuation",
        "margin_of_safety",
        "risk",
        "recommendation",
        "business_quality",
    }
)


def severity_from_diff(diff: Mapping[str, Any]) -> str:
    """Deterministic severity from structural diff metadata — not a score."""
    summary = diff.get("change_summary") if isinstance(diff.get("change_summary"), Mapping) else {}
    if summary.get("identical_content"):
        return "info"
    sections = diff.get("sections") if isinstance(diff.get("sections"), list) else []
    changed_names = {
        str(s.get("name"))
        for s in sections
        if isinstance(s, Mapping) and s.get("status") in {"changed", "added", "removed"}
    }
    if changed_names & IMPORTANT_SECTIONS:
        return "important"
    if int(summary.get("fields_changed") or 0) or int(summary.get("fields_added") or 0) or int(
        summary.get("fields_removed") or 0
    ):
        return "watch"
    return "info"


def _citations_from_diff(diff: Mapping[str, Any], subject: str) -> tuple[dict[str, Any], ...]:
    citations: list[dict[str, Any]] = []
    sections = diff.get("sections") if isinstance(diff.get("sections"), list) else []
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        if section.get("status") == "unchanged":
            continue
        name = str(section.get("name") or "")
        citations.append(
            {
                "symbol": subject,
                "source_kind": "research_diff",
                "section": name,
                "path": f"research_diff.{name}",
                "available": True,
                "label": f"diff/{name}",
                "diff_id": diff.get("diff_id"),
                "status": section.get("status"),
            }
        )
        for field in section.get("field_diffs") or []:
            if not isinstance(field, Mapping):
                continue
            citations.append(
                {
                    "symbol": subject,
                    "source_kind": "research_diff",
                    "section": name,
                    "path": str(field.get("path") or f"research_diff.{name}"),
                    "available": True,
                    "label": str(field.get("path") or name),
                    "diff_id": diff.get("diff_id"),
                    "status": field.get("status"),
                }
            )
    citations.sort(key=lambda c: (c["section"], c["path"]))
    return tuple(citations)


def alerts_from_diff(
    *,
    subject: str,
    subject_kind: str,
    diff: Mapping[str, Any],
    baseline_snapshot_id: str | None,
    current_snapshot_id: str | None,
    alert_id: str | None = None,
) -> MonitoringAlert | None:
    summary = diff.get("change_summary") if isinstance(diff.get("change_summary"), Mapping) else {}
    if summary.get("identical_content"):
        return None
    severity = severity_from_diff(diff)
    citations = _citations_from_diff(diff, subject)
    if not citations:
        citations = (
            {
                "symbol": subject,
                "source_kind": "research_diff",
                "section": "change_summary",
                "path": "research_diff.change_summary",
                "available": True,
                "label": "diff/change_summary",
                "diff_id": diff.get("diff_id"),
            },
        )
    message = (
        f"Research change detected for {subject}: "
        f"fields_changed={summary.get('fields_changed', 0)}, "
        f"sections_changed={summary.get('sections_changed', 0)}."
    )
    return MonitoringAlert(
        alert_id=alert_id or str(uuid4()),
        severity=severity,
        subject=subject,
        subject_kind=subject_kind,
        alert_type="research_change",
        message=message,
        citations=tuple(freeze_mapping(c) or {} for c in citations),
        diff_id=str(diff.get("diff_id")) if diff.get("diff_id") else None,
        baseline_snapshot_id=baseline_snapshot_id,
        current_snapshot_id=current_snapshot_id,
        change_summary=freeze_mapping(dict(summary)) or freeze_mapping({}),
        provenance=freeze_mapping(
            {
                "source": "research_monitoring",
                "via": "research_diff",
                "left_snapshot_id": diff.get("left_snapshot_id"),
                "right_snapshot_id": diff.get("right_snapshot_id"),
            }
        )
        or freeze_mapping({}),
    )


def alerts_from_portfolio_intelligence(
    *,
    portfolio_id: str,
    baseline: Mapping[str, Any] | None,
    current: Mapping[str, Any] | None,
    alert_id_prefix: str | None = None,
) -> tuple[MonitoringAlert, ...]:
    """Compare two A002 result dicts structurally for missing-research changes only.

    No optimisation or new scores — detects membership / missing-research deltas.
    """
    alerts: list[MonitoringAlert] = []
    if baseline is None and current is None:
        return ()
    if baseline is None or current is None:
        alerts.append(
            MonitoringAlert(
                alert_id=f"{alert_id_prefix or 'pi'}-unavailable",
                severity="unavailable",
                subject=portfolio_id,
                subject_kind="portfolio",
                alert_type="portfolio_context_missing",
                message=UNAVAILABLE_MESSAGE,
                citations=(
                    freeze_mapping(
                        {
                            "source_kind": "portfolio_intelligence",
                            "section": "result",
                            "path": "portfolio_intelligence",
                            "available": False,
                            "label": "portfolio_intelligence",
                        }
                    )
                    or {},
                ),
                provenance=freeze_mapping(
                    {"source": "research_monitoring", "via": "portfolio_intelligence"}
                )
                or freeze_mapping({}),
            )
        )
        return tuple(alerts)

    base_missing = {
        str(m.get("symbol"))
        for m in (baseline.get("missing_research") or [])
        if isinstance(m, Mapping) and m.get("symbol")
    }
    curr_missing = {
        str(m.get("symbol"))
        for m in (current.get("missing_research") or [])
        if isinstance(m, Mapping) and m.get("symbol")
    }
    newly_missing = sorted(curr_missing - base_missing)
    recovered = sorted(base_missing - curr_missing)

    for sym in newly_missing:
        alerts.append(
            MonitoringAlert(
                alert_id=f"{alert_id_prefix or 'pi'}-missing-{sym}",
                severity="important",
                subject=portfolio_id,
                subject_kind="portfolio",
                alert_type="portfolio_missing_research",
                message=f"Holding {sym} research became unavailable.",
                citations=(
                    freeze_mapping(
                        {
                            "symbol": sym,
                            "source_kind": "portfolio_intelligence",
                            "section": "missing_research",
                            "path": f"portfolio_intelligence.missing_research.{sym}",
                            "available": False,
                            "label": f"missing/{sym}",
                        }
                    )
                    or {},
                ),
                change_summary=freeze_mapping(
                    {"symbol": sym, "status": "became_missing"}
                )
                or freeze_mapping({}),
                provenance=freeze_mapping(
                    {
                        "source": "research_monitoring",
                        "via": "portfolio_intelligence",
                        "baseline_result_id": baseline.get("result_id"),
                        "current_result_id": current.get("result_id"),
                    }
                )
                or freeze_mapping({}),
            )
        )
    for sym in recovered:
        alerts.append(
            MonitoringAlert(
                alert_id=f"{alert_id_prefix or 'pi'}-recovered-{sym}",
                severity="watch",
                subject=portfolio_id,
                subject_kind="portfolio",
                alert_type="portfolio_research_recovered",
                message=f"Holding {sym} research is linked again.",
                citations=(
                    freeze_mapping(
                        {
                            "symbol": sym,
                            "source_kind": "portfolio_intelligence",
                            "section": "linked_holdings",
                            "path": f"portfolio_intelligence.linked_holdings.{sym}",
                            "available": True,
                            "label": f"linked/{sym}",
                        }
                    )
                    or {},
                ),
                change_summary=freeze_mapping(
                    {"symbol": sym, "status": "recovered"}
                )
                or freeze_mapping({}),
                provenance=freeze_mapping(
                    {
                        "source": "research_monitoring",
                        "via": "portfolio_intelligence",
                        "baseline_result_id": baseline.get("result_id"),
                        "current_result_id": current.get("result_id"),
                    }
                )
                or freeze_mapping({}),
            )
        )

    # Linked MoS pass-through change detection (equality only)
    def _mos_map(result: Mapping[str, Any]) -> dict[str, Any]:
        summary = result.get("margin_of_safety_summary")
        if not isinstance(summary, Mapping):
            return {}
        positions = summary.get("positions") or []
        out: dict[str, Any] = {}
        if isinstance(positions, list):
            for row in positions:
                if isinstance(row, Mapping) and row.get("symbol"):
                    out[str(row["symbol"])] = row.get("margin_of_safety")
        return out

    base_mos = _mos_map(baseline)
    curr_mos = _mos_map(current)
    for sym in sorted(set(base_mos) | set(curr_mos)):
        if base_mos.get(sym) == curr_mos.get(sym):
            continue
        left = base_mos.get(sym, UNAVAILABLE_MESSAGE)
        right = curr_mos.get(sym, UNAVAILABLE_MESSAGE)
        alerts.append(
            MonitoringAlert(
                alert_id=f"{alert_id_prefix or 'pi'}-mos-{sym}",
                severity="important",
                subject=portfolio_id,
                subject_kind="portfolio",
                alert_type="portfolio_mos_change",
                message=f"Linked margin_of_safety changed for {sym}.",
                citations=(
                    freeze_mapping(
                        {
                            "symbol": sym,
                            "source_kind": "portfolio_intelligence",
                            "section": "margin_of_safety_summary",
                            "path": f"portfolio_intelligence.margin_of_safety_summary.{sym}",
                            "available": right != UNAVAILABLE_MESSAGE,
                            "label": f"mos/{sym}",
                            "left_value": left,
                            "right_value": right,
                        }
                    )
                    or {},
                ),
                change_summary=freeze_mapping(
                    {"symbol": sym, "left": left, "right": right}
                )
                or freeze_mapping({}),
                provenance=freeze_mapping(
                    {
                        "source": "research_monitoring",
                        "via": "portfolio_intelligence",
                    }
                )
                or freeze_mapping({}),
            )
        )
    return tuple(alerts)
