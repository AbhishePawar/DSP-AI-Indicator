"""Multi-instrument coverage index over refresh + promoted snapshots."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from dsp_platform.share_count_refresh import (
    CoverageState,
    InstrumentIdentity,
    ShareCountObservation,
    ShareCountRefreshRequest,
    refresh_share_count,
)

__all__ = ["CoverageRow", "ShareCountCoverageIndex"]


@dataclass(frozen=True, slots=True)
class CoverageRow:
    identity: InstrumentIdentity
    state: CoverageState
    reason: str
    shares_outstanding: Decimal | None
    complete_through: object
    has_candidate: bool
    has_promoted_snapshot: bool


class ShareCountCoverageIndex:
    """Answer which identities are current, stale, candidate, or unsupported."""

    def __init__(self, rows: tuple[CoverageRow, ...]) -> None:
        self.rows = rows

    @classmethod
    def evaluate(
        cls,
        identities: Sequence[InstrumentIdentity],
        *,
        lookup_horizon: datetime,
        snapshots: Mapping[str, Mapping[str, Any]] | None = None,
        observations: Mapping[str, ShareCountObservation] | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> ShareCountCoverageIndex:
        snap_map = snapshots or {}
        obs_map = observations or {}
        ev_map = evidence or {}
        rows: list[CoverageRow] = []
        for identity in identities:
            key = _key(identity)
            snapshot = snap_map.get(key)
            result = refresh_share_count(
                ShareCountRefreshRequest(
                    identity=identity,
                    lookup_horizon=lookup_horizon,
                    current_snapshot=snapshot,
                    corporate_action_evidence=ev_map.get(key),
                    observation=obs_map.get(key),
                    observation_source_id=(
                        "promoted_snapshot_artifact"
                        if snapshot is not None
                        else "t1_issuer_disclosure"
                    ),
                )
            )
            rows.append(
                CoverageRow(
                    identity=identity.normalized(),
                    state=result.state,
                    reason=result.reason,
                    shares_outstanding=result.shares_outstanding,
                    complete_through=result.complete_through,
                    has_candidate=result.candidate is not None,
                    has_promoted_snapshot=snapshot is not None,
                )
            )
        return cls(tuple(rows))

    def current(self) -> tuple[CoverageRow, ...]:
        return tuple(row for row in self.rows if row.state is CoverageState.CURRENT)

    def stale(self) -> tuple[CoverageRow, ...]:
        return tuple(row for row in self.rows if row.state is CoverageState.STALE)

    def candidates(self) -> tuple[CoverageRow, ...]:
        return tuple(
            row
            for row in self.rows
            if row.state is CoverageState.VALIDATED or row.has_candidate
        )

    def need_evidence(self) -> tuple[CoverageRow, ...]:
        wanted = {
            CoverageState.DISCOVERED,
            CoverageState.CANDIDATE,
            CoverageState.REFRESH_PENDING,
            CoverageState.STALE,
        }
        return tuple(row for row in self.rows if row.state in wanted)

    def unsupported(self) -> tuple[CoverageRow, ...]:
        wanted = {
            CoverageState.UNKNOWN,
            CoverageState.UNAVAILABLE,
            CoverageState.INVALID,
        }
        return tuple(row for row in self.rows if row.state in wanted)


def _key(identity: InstrumentIdentity) -> str:
    n = identity.normalized()
    return f"{n.isin}_{n.mic}"
