"""Retention policy hooks (EPIC-R004) — advisory only; never mutate snapshots."""

from __future__ import annotations

from typing import Protocol

from dsp_platform.research_archive.models import (
    ArchiveSnapshot,
    RetentionDecision,
    utc_now,
)

__all__ = [
    "RetainForeverPolicy",
    "RetentionPolicy",
    "TimeToLivePolicy",
]


class RetentionPolicy(Protocol):
    """Hook interface — evaluate only; archive content stays immutable."""

    @property
    def policy_id(self) -> str: ...

    def evaluate(self, snapshot: ArchiveSnapshot) -> RetentionDecision: ...


class RetainForeverPolicy:
    """Default policy — always retain."""

    policy_id = "retain_forever"

    def evaluate(self, snapshot: ArchiveSnapshot) -> RetentionDecision:
        return RetentionDecision(
            retain=True,
            reason="default retain-forever policy",
            policy_id=self.policy_id,
            expires_at=None,
            evaluated_at=utc_now().isoformat(),
        )


class TimeToLivePolicy:
    """Advisory TTL based on archived_at ISO timestamp (no deletion)."""

    def __init__(self, *, ttl_seconds: int, policy_id: str = "ttl") -> None:
        if ttl_seconds < 0:
            raise ValueError("ttl_seconds must be >= 0")
        self._ttl_seconds = ttl_seconds
        self.policy_id = policy_id

    def evaluate(self, snapshot: ArchiveSnapshot) -> RetentionDecision:
        from datetime import datetime

        evaluated_at = utc_now()
        try:
            archived = datetime.fromisoformat(snapshot.archived_at)
            if archived.tzinfo is None:
                from datetime import UTC

                archived = archived.replace(tzinfo=UTC)
        except ValueError:
            return RetentionDecision(
                retain=True,
                reason="unparseable archived_at; default retain",
                policy_id=self.policy_id,
                expires_at=None,
                evaluated_at=evaluated_at.isoformat(),
            )

        age = (evaluated_at - archived).total_seconds()
        retain = age <= self._ttl_seconds
        expires_at = None
        try:
            from datetime import timedelta

            expires_at = (archived + timedelta(seconds=self._ttl_seconds)).isoformat()
        except Exception:  # noqa: BLE001
            expires_at = None
        return RetentionDecision(
            retain=retain,
            reason=(
                "within TTL"
                if retain
                else f"age_seconds={int(age)} exceeds ttl_seconds={self._ttl_seconds}"
            ),
            policy_id=self.policy_id,
            expires_at=expires_at,
            evaluated_at=evaluated_at.isoformat(),
        )
