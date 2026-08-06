"""Research Intelligence service (EPIC-011B).

Pure measurement consumer: capture immutable snapshots, track history,
measure outcomes, calibrate confidence, and surface intelligence.
Never invokes valuation / recommendation engines.
"""

from __future__ import annotations

from typing import Any, Mapping

from dsp_platform.research_intelligence.calibration import build_calibration_report
from dsp_platform.research_intelligence.capture import build_snapshot_from_analyse_payload
from dsp_platform.research_intelligence.dashboard import build_performance_dashboard
from dsp_platform.research_intelligence.insights import build_insight_bundle
from dsp_platform.research_intelligence.models import (
    OUTCOME_WINDOWS_MONTHS,
    RI_SCHEMA_VERSION,
    RI_SERVICE_VERSION,
    ResearchSnapshot,
)
from dsp_platform.research_intelligence.outcomes import (
    measure_outcome,
    measure_outcomes_for_snapshot,
)
from dsp_platform.research_intelligence.store import (
    InMemoryResearchSnapshotStore,
    ResearchSnapshotStore,
    SnapshotAlreadyExistsError,
)
from dsp_platform.research_intelligence.validation import (
    validate_research_snapshot,
    validate_window_months,
)

__all__ = [
    "RI_SERVICE_VERSION",
    "ResearchIntelligenceService",
    "capture_research_snapshot",
    "get_default_service",
]


class ResearchIntelligenceService:
    def __init__(self, store: ResearchSnapshotStore | None = None) -> None:
        self._store: ResearchSnapshotStore = store or InMemoryResearchSnapshotStore()

    @property
    def store(self) -> ResearchSnapshotStore:
        return self._store

    def capture_from_payload(
        self,
        payload: Mapping[str, Any],
        *,
        research_id: str | None = None,
        timestamp: str | None = None,
        ticker: str | None = None,
        company: str | None = None,
        exchange: str | None = None,
        research_version: str | None = None,
        model_version: str | None = None,
        allow_duplicate: bool = False,
    ) -> dict[str, Any]:
        snapshot = build_snapshot_from_analyse_payload(
            payload,
            research_id=research_id,
            timestamp=timestamp,
            ticker=ticker,
            company=company,
            exchange=exchange,
            research_version=research_version,
            model_version=model_version,
        )
        validate_research_snapshot(snapshot)
        try:
            self._store.put_if_absent(snapshot)
        except SnapshotAlreadyExistsError:
            if not allow_duplicate:
                raise
            existing = self._store.get(snapshot.research_id)
            if existing is not None:
                return {
                    "ok": True,
                    "duplicate": True,
                    "snapshot": existing.to_dict(),
                }
            raise
        return {"ok": True, "duplicate": False, "snapshot": snapshot.to_dict()}

    def register_snapshot(self, snapshot: ResearchSnapshot) -> dict[str, Any]:
        validate_research_snapshot(snapshot)
        self._store.put_if_absent(snapshot)
        return {"ok": True, "duplicate": False, "snapshot": snapshot.to_dict()}

    def get_snapshot(self, research_id: str) -> dict[str, Any] | None:
        snap = self._store.get(research_id)
        return snap.to_dict() if snap else None

    def list_snapshots(
        self,
        *,
        symbol: str | None = None,
        company: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> dict[str, Any]:
        if symbol:
            snaps = self._store.list_by_symbol(symbol)
        elif company:
            snaps = self._store.list_by_company(company)
        else:
            snaps = self._store.list_all()
        total = len(snaps)
        sliced = snaps[offset:]
        if limit is not None:
            sliced = sliced[: max(0, limit)]
        return {
            "ok": True,
            "total": total,
            "offset": offset,
            "limit": limit,
            "snapshots": [s.to_dict() for s in sliced],
            "windows_supported": list(OUTCOME_WINDOWS_MONTHS),
        }

    def timeline(
        self,
        *,
        symbol: str | None = None,
        company: str | None = None,
        limit: int | None = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        listing = self.list_snapshots(
            symbol=symbol, company=company, limit=limit, offset=offset
        )
        evolution = [
            {
                "research_id": s["research_id"],
                "timestamp": s["timestamp"],
                "recommendation": s.get("recommendation"),
                "confidence": s.get("confidence"),
                "confidence_label": s.get("confidence_label"),
                "price": s.get("price"),
                "intrinsic_value": s.get("intrinsic_value"),
                "margin_of_safety": s.get("margin_of_safety"),
                "research_version": s.get("research_version"),
                "model_version": s.get("model_version"),
                "content_sha256": s.get("content_sha256"),
            }
            for s in listing["snapshots"]
        ]
        return {
            "ok": True,
            "total": listing["total"],
            "offset": offset,
            "limit": limit,
            "timeline": evolution,
            "provenance": {
                "source": "research_intelligence",
                "engines_called": False,
                "immutable": True,
            },
        }

    def measure(
        self,
        research_id: str,
        *,
        window_months: int,
        price_at_horizon: float | None = None,
        iv_at_horizon: float | None = None,
        measured_at: str | None = None,
    ) -> dict[str, Any]:
        validate_window_months(window_months)
        snap = self._store.get(research_id)
        if snap is None:
            raise KeyError(f"snapshot not found: {research_id}")
        outcome = measure_outcome(
            snap,
            window_months=window_months,
            price_at_horizon=price_at_horizon,
            iv_at_horizon=iv_at_horizon,
            measured_at=measured_at,
        )
        return {"ok": True, "outcome": outcome.to_dict()}

    def measure_batch(
        self,
        *,
        window_months: int,
        horizon_prices: Mapping[str, float | None] | None = None,
        measured_at: str | None = None,
    ) -> dict[str, Any]:
        """Measure all snapshots for a window using optional per-id horizon prices."""
        validate_window_months(window_months)
        prices = dict(horizon_prices or {})
        outcomes = []
        for snap in self._store.list_all():
            outcomes.append(
                measure_outcome(
                    snap,
                    window_months=window_months,
                    price_at_horizon=prices.get(snap.research_id),
                    measured_at=measured_at,
                ).to_dict()
            )
        return {
            "ok": True,
            "window_months": window_months,
            "outcomes": outcomes,
            "count": len(outcomes),
        }

    def calibration(
        self,
        *,
        window_months: int,
        horizon_prices: Mapping[str, float | None] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        measured_at: str | None = None,
    ) -> dict[str, Any]:
        validate_window_months(window_months)
        prices = dict(horizon_prices or {})
        outcomes = tuple(
            measure_outcome(
                snap,
                window_months=window_months,
                price_at_horizon=prices.get(snap.research_id),
                measured_at=measured_at,
            )
            for snap in self._store.list_all()
        )
        report = build_calibration_report(
            outcomes,
            window_months=window_months,
            result_id=result_id,
            created_at=created_at,
        )
        return {"ok": True, "calibration": report.to_dict()}

    def performance_dashboard(
        self,
        *,
        window_months: int,
        horizon_prices: Mapping[str, float | None] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        measured_at: str | None = None,
    ) -> dict[str, Any]:
        validate_window_months(window_months)
        snaps = self._store.list_all()
        prices = dict(horizon_prices or {})
        outcomes = tuple(
            measure_outcome(
                snap,
                window_months=window_months,
                price_at_horizon=prices.get(snap.research_id),
                measured_at=measured_at,
            )
            for snap in snaps
        )
        dash = build_performance_dashboard(
            snaps,
            outcomes,
            window_months=window_months,
            result_id=result_id,
            created_at=created_at,
        )
        return {"ok": True, "dashboard": dash.to_dict()}

    def insights(
        self,
        *,
        window_months: int,
        horizon_prices: Mapping[str, float | None] | None = None,
        result_id: str | None = None,
        created_at: str | None = None,
        measured_at: str | None = None,
        top_n: int = 5,
    ) -> dict[str, Any]:
        validate_window_months(window_months)
        snaps = self._store.list_all()
        prices = dict(horizon_prices or {})
        outcomes = tuple(
            measure_outcome(
                snap,
                window_months=window_months,
                price_at_horizon=prices.get(snap.research_id),
                measured_at=measured_at,
            )
            for snap in snaps
        )
        bundle = build_insight_bundle(
            snaps,
            outcomes,
            window_months=window_months,
            result_id=result_id,
            created_at=created_at,
            top_n=top_n,
        )
        return {"ok": True, "insights": bundle.to_dict()}

    def schema(self) -> dict[str, Any]:
        return {
            "schema_version": RI_SCHEMA_VERSION,
            "service_version": RI_SERVICE_VERSION,
            "measurement_only": True,
            "windows_months": list(OUTCOME_WINDOWS_MONTHS),
            "rules": [
                "immutable_snapshots",
                "never_overwrite",
                "no_engine_calls",
                "no_recommendation_rewrite",
                "missing_is_data_unavailable",
                "unable_to_calculate_when_incomplete",
            ],
            "endpoints": [
                "/research/intelligence/schema",
                "/research/intelligence/snapshots",
                "/research/intelligence/timeline",
                "/research/intelligence/outcomes",
                "/research/intelligence/calibration",
                "/research/intelligence/performance",
                "/research/intelligence/insights",
            ],
        }


def get_default_service() -> ResearchIntelligenceService:
    from dsp_platform.research_intelligence.registry import (
        get_research_intelligence_service,
    )

    return get_research_intelligence_service()


def capture_research_snapshot(
    payload: Mapping[str, Any], **kwargs: Any
) -> dict[str, Any]:
    return get_default_service().capture_from_payload(payload, **kwargs)
