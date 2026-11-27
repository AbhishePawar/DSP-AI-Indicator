"""Governed macroeconomic evidence for canonical investment research."""

from dataclasses import asdict
from datetime import date

from dsp_platform.world_bank_adapter import (
    WorldBankEconomicAdapter,
)

from snapshot_bridge.economic import (
    EconomicSnapshotBuilder,
)


INDIAN_EXCHANGES = frozenset({
    "NSE",
    "BSE",
    "AMFI",
})

REQUIRED_CODES = (
    "GDP_GROWTH",
    "INFLATION_RATE",
)


class MacroeconomicEvidenceService:

    def __init__(self, adapter=None):

        self._adapter = (
            adapter if adapter is not None
            else WorldBankEconomicAdapter()
        )

    def acquire(self, *, exchange, as_of=None):

        exchange = str(
            exchange or ""
        ).strip().upper()

        if exchange not in INDIAN_EXCHANGES:

            return {
                "status": "unavailable",
                "reason": "unsupported_or_unresolved_exchange",
                "country": None,
                "snapshot": None,
                "sources": [],
                "authorized_for_valuation": False,
            }

        today = date.today()

        if as_of is not None and as_of != today:

            return {
                "status": "unavailable",
                "reason": "point_in_time_evidence_not_supported",
                "country": "IN",
                "snapshot": None,
                "sources": [],
                "authorized_for_valuation": False,
            }

        series = {}
        sources = []
        failures = []

        for code in REQUIRED_CODES:

            try:

                normalized, evidence = (
                    self._adapter.acquire_with_evidence(
                        code, "IN"
                    )
                )

                if (
                    normalized.country != "IN"
                    or normalized.indicator_code != code
                ):

                    raise ValueError(
                        "Economic identity mismatch"
                    )

                if any(
                    point.observation_date > today
                    for point in normalized.points
                ):

                    raise ValueError(
                        "Future economic observation"
                    )

                series[code] = normalized

                sources.append({
                    "indicator": code,
                    "source": evidence.get("source"),
                    "source_url": evidence.get("source_url"),
                    "content_hash": evidence.get("content_hash"),
                    "retrieved_at": evidence.get("retrieved_at"),
                    "dataset_last_updated": evidence.get(
                        "dataset_last_updated"
                    ),
                    "observation_period": (
                        normalized.points[-1]
                        .observation_date.isoformat()
                    ),
                    "unit": normalized.unit,
                    "observations": len(normalized.points),
                })

            except Exception as exc:

                failures.append({
                    "indicator": code,
                    "reason": type(exc).__name__,
                })

        snapshot = None

        if series:

            try:

                result = EconomicSnapshotBuilder.build(
                    series,
                    country="IN",
                )

                snapshot = asdict(result)

                snapshot["as_of"] = (
                    result.as_of.isoformat()
                )

            except Exception as exc:

                failures.append({
                    "indicator": "snapshot",
                    "reason": type(exc).__name__,
                })

        status = (
            "unavailable" if snapshot is None
            else "partial"
        )

        return {
            "status": status,
            "country": "IN",
            "snapshot": snapshot,
            "sources": sources,
            "failures": failures,
            "available_indicators": sorted(series),
            "missing_indicators": [
                code for code in REQUIRED_CODES
                if code not in series
            ],
            "evidence_class": "public_macroeconomic_dataset",
            "historical_point_in_time_verified": False,
            "authorized_for_valuation": False,
            "limitations": [
                "Annual observations are not real-time data.",
                "Observation dates are period labels.",
                "Historical publication vintages are unavailable.",
                "Macroeconomic coverage remains incomplete.",
            ],
        }
