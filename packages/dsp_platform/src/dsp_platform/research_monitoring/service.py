"""Continuous Research Monitoring service (EPIC-A003)."""

from __future__ import annotations

import uuid
from typing import Any, Mapping

from dsp_platform.research_diff import diff_research_snapshots, research_diff_to_dict
from dsp_platform.research_monitoring.alerts import (
    alerts_from_diff,
    alerts_from_portfolio_intelligence,
)
from dsp_platform.research_monitoring.models import (
    MONITORING_SCHEMA_VERSION,
    MONITORING_SERVICE_VERSION,
    MonitoringAlert,
    MonitoringEvaluateResult,
    SnapshotTrack,
    UNAVAILABLE_MESSAGE,
    freeze_mapping,
    utc_now,
)
from dsp_platform.research_monitoring.registry import get_monitoring_registry
from dsp_platform.research_monitoring.serde import monitoring_result_to_dict
from dsp_platform.research_monitoring.validation import validate_monitoring_result
from dsp_platform.research_archive.store import SnapshotNotFoundError

__all__ = [
    "MONITORING_SERVICE_VERSION",
    "ResearchMonitoringService",
    "evaluate_research_monitoring",
]


class ResearchMonitoringService:
    """Detect changes via R005 diffs + A002 result comparisons — read-only."""

    def register_watchlist(self, symbols: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        return get_monitoring_registry().register_watchlist(symbols)

    def register_portfolio(
        self, portfolio_id: str, *, metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return get_monitoring_registry().register_portfolio(
            portfolio_id, metadata=metadata
        )

    def track_snapshot(
        self,
        subject: str,
        *,
        subject_kind: str = "symbol",
        baseline_snapshot_id: str | None = None,
        current_snapshot_id: str | None = None,
        tracked_at: str | None = None,
    ) -> SnapshotTrack:
        return get_monitoring_registry().track_snapshot(
            subject,
            subject_kind=subject_kind,
            baseline_snapshot_id=baseline_snapshot_id,
            current_snapshot_id=current_snapshot_id,
            tracked_at=tracked_at,
        )

    def evaluate(
        self,
        *,
        # Optional explicit pairs override registry tracks
        snapshot_pairs: Mapping[str, Mapping[str, str]] | None = None,
        portfolio_intelligence_baseline: Mapping[str, Any] | None = None,
        portfolio_intelligence_current: Mapping[str, Any] | None = None,
        portfolio_id: str | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        register_watchlist_symbols: list[str] | None = None,
    ) -> MonitoringEvaluateResult:
        registry = get_monitoring_registry()
        if register_watchlist_symbols:
            registry.register_watchlist(register_watchlist_symbols)

        alerts: list[MonitoringAlert] = []
        tracks: list[SnapshotTrack] = []

        pairs: dict[str, Mapping[str, str]] = {}
        if snapshot_pairs:
            pairs.update({str(k).upper(): v for k, v in snapshot_pairs.items()})
        else:
            for track in registry.tracks():
                if track.subject_kind != "symbol":
                    continue
                if track.baseline_snapshot_id and track.current_snapshot_id:
                    pairs[track.subject] = {
                        "baseline_snapshot_id": track.baseline_snapshot_id,
                        "current_snapshot_id": track.current_snapshot_id,
                    }

        for subject in sorted(pairs.keys()):
            pair = pairs[subject]
            baseline_id = pair.get("baseline_snapshot_id")
            current_id = pair.get("current_snapshot_id")
            track = SnapshotTrack(
                subject=subject,
                subject_kind="symbol",
                baseline_snapshot_id=baseline_id,
                current_snapshot_id=current_id,
                tracked_at=created_at or utc_now().isoformat(),
            )
            tracks.append(track)
            if not baseline_id or not current_id:
                alerts.append(
                    MonitoringAlert(
                        alert_id=f"mon-unavail-{subject}",
                        severity="unavailable",
                        subject=subject,
                        subject_kind="symbol",
                        alert_type="snapshot_missing",
                        message=UNAVAILABLE_MESSAGE,
                        citations=(
                            freeze_mapping(
                                {
                                    "symbol": subject,
                                    "source_kind": "research_archive",
                                    "section": "snapshot",
                                    "path": f"archive.{subject}",
                                    "available": False,
                                    "label": f"archive/{subject}",
                                }
                            )
                            or {},
                        ),
                        baseline_snapshot_id=baseline_id,
                        current_snapshot_id=current_id,
                        provenance=freeze_mapping(
                            {"source": "research_monitoring", "via": "snapshot_tracker"}
                        )
                        or freeze_mapping({}),
                    )
                )
                continue
            try:
                diff = research_diff_to_dict(
                    diff_research_snapshots(
                        baseline_id,
                        current_id,
                        diff_id=f"mon-diff-{subject}",
                        created_at=created_at,
                    )
                )
            except SnapshotNotFoundError:
                alerts.append(
                    MonitoringAlert(
                        alert_id=f"mon-missing-{subject}",
                        severity="unavailable",
                        subject=subject,
                        subject_kind="symbol",
                        alert_type="snapshot_not_found",
                        message=UNAVAILABLE_MESSAGE,
                        citations=(
                            freeze_mapping(
                                {
                                    "symbol": subject,
                                    "source_kind": "research_archive",
                                    "section": "snapshot",
                                    "path": f"archive.{subject}",
                                    "available": False,
                                    "label": f"archive/{subject}",
                                }
                            )
                            or {},
                        ),
                        baseline_snapshot_id=baseline_id,
                        current_snapshot_id=current_id,
                        provenance=freeze_mapping(
                            {"source": "research_monitoring", "via": "research_archive"}
                        )
                        or freeze_mapping({}),
                    )
                )
                continue
            except ValueError as exc:
                alerts.append(
                    MonitoringAlert(
                        alert_id=f"mon-error-{subject}",
                        severity="unavailable",
                        subject=subject,
                        subject_kind="symbol",
                        alert_type="diff_unavailable",
                        message=UNAVAILABLE_MESSAGE,
                        citations=(
                            freeze_mapping(
                                {
                                    "symbol": subject,
                                    "source_kind": "research_diff",
                                    "section": "diff",
                                    "path": f"research_diff.{subject}",
                                    "available": False,
                                    "label": f"diff/{subject}",
                                    "error": str(exc),
                                }
                            )
                            or {},
                        ),
                        baseline_snapshot_id=baseline_id,
                        current_snapshot_id=current_id,
                        provenance=freeze_mapping(
                            {"source": "research_monitoring", "via": "research_diff"}
                        )
                        or freeze_mapping({}),
                    )
                )
                continue

            alert = alerts_from_diff(
                subject=subject,
                subject_kind="symbol",
                diff=diff,
                baseline_snapshot_id=baseline_id,
                current_snapshot_id=current_id,
                alert_id=f"mon-change-{subject}",
            )
            if alert is not None:
                alerts.append(alert)

        if (
            portfolio_intelligence_baseline is not None
            or portfolio_intelligence_current is not None
        ):
            pid: Any = portfolio_id
            if not pid and isinstance(portfolio_intelligence_current, Mapping):
                portfolio_block = portfolio_intelligence_current.get("portfolio") or {}
                if isinstance(portfolio_block, Mapping):
                    pid = portfolio_block.get("portfolio_id")
            if not pid and isinstance(portfolio_intelligence_baseline, Mapping):
                portfolio_block = portfolio_intelligence_baseline.get("portfolio") or {}
                if isinstance(portfolio_block, Mapping):
                    pid = portfolio_block.get("portfolio_id")
            pid = str(pid or "portfolio")
            alerts.extend(
                alerts_from_portfolio_intelligence(
                    portfolio_id=pid,
                    baseline=portfolio_intelligence_baseline,
                    current=portfolio_intelligence_current,
                    alert_id_prefix=f"mon-pi-{pid}",
                )
            )

        created = created_at or utc_now().isoformat()
        rid = result_id or str(uuid.uuid4())
        watchlist = {"symbols": list(registry.watchlist())}
        portfolios = registry.portfolios()
        provenance = {
            "source": "research_monitoring",
            "service_version": MONITORING_SERVICE_VERSION,
            "providers_called": False,
            "engines_called": False,
            "diff_engine": "research_diff",
        }
        audit = {
            "result_id": rid,
            "created_at": created,
            "alert_count": len(alerts),
            "track_count": len(tracks),
            "watchlist_count": len(watchlist["symbols"]),
            "portfolio_count": len(portfolios),
        }
        limitations = (
            "Reports structural changes from R005 diffs and A002 summaries only.",
            "No valuation, scoring, optimisation, or recommendations.",
            "No providers or engines executed.",
        )
        # Deterministic alert order
        alerts_sorted = tuple(
            sorted(alerts, key=lambda a: (a.subject, a.alert_type, a.alert_id))
        )
        tracks_sorted = tuple(
            sorted(tracks, key=lambda t: (t.subject_kind, t.subject))
        )
        result = MonitoringEvaluateResult(
            result_id=rid,
            schema_version=MONITORING_SCHEMA_VERSION,
            service_version=MONITORING_SERVICE_VERSION,
            created_at=created,
            watchlist=freeze_mapping(watchlist) or freeze_mapping({}),
            portfolios=freeze_mapping(portfolios) or freeze_mapping({}),
            tracks=tracks_sorted,
            alerts=alerts_sorted,
            provenance=freeze_mapping(provenance) or freeze_mapping({}),
            audit=freeze_mapping(audit) or freeze_mapping({}),
            limitations=limitations,
        )
        validate_monitoring_result(result)
        return result


def evaluate_research_monitoring(**kwargs: Any) -> dict[str, Any]:
    result = ResearchMonitoringService().evaluate(**kwargs)
    return monitoring_result_to_dict(result)
