"""DPDP consent ports and reference adapters (PEP-004)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any, Protocol, Sequence, runtime_checkable

__all__ = [
    "ConsentPort",
    "ConsentPurpose",
    "ConsentRecord",
    "ConsentVersion",
    "InMemoryConsentPort",
]


@dataclass(frozen=True, slots=True)
class ConsentPurpose:
    """Lawful purpose tag under DPDP purpose limitation."""

    purpose_id: str
    label: str
    description: str
    required: bool = False


@dataclass(frozen=True, slots=True)
class ConsentVersion:
    """Versioned consent policy / notice text."""

    version: str
    effective_at: datetime
    notice_text: str
    purposes: tuple[ConsentPurpose, ...] = ()


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    """Immutable consent decision for a data principal."""

    consent_id: str
    subject_id: str
    purpose_id: str
    granted: bool
    policy_version: str
    recorded_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    locale: str = "en-IN"
    channel: str = "app"
    metadata: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class ConsentPort(Protocol):
    """DPDP consent record store — versioned purposes."""

    def current_policy(self) -> ConsentVersion:
        """Return the active consent policy version."""

    def record(self, consent: ConsentRecord) -> ConsentRecord:
        """Append an immutable consent decision."""

    def list_for_subject(self, subject_id: str) -> Sequence[ConsentRecord]:
        """List consents for a data principal."""

    def latest_for_purpose(
        self, subject_id: str, purpose_id: str
    ) -> ConsentRecord | None:
        """Return the latest decision for a purpose, if any."""

    def withdraw(self, subject_id: str, purpose_id: str, *, policy_version: str) -> ConsentRecord:
        """Record a withdrawal (granted=False)."""


DEFAULT_PURPOSES: tuple[ConsentPurpose, ...] = (
    ConsentPurpose(
        purpose_id="account_administration",
        label="Account administration",
        description="Create and secure your DSP account.",
        required=True,
    ),
    ConsentPurpose(
        purpose_id="research_analytics",
        label="Research analytics",
        description="Process research sessions to improve educational insights.",
        required=False,
    ),
    ConsentPurpose(
        purpose_id="audit_retention",
        label="Security & audit retention",
        description="Retain security and compliance audit logs per CERT-In posture.",
        required=True,
    ),
)


def default_consent_policy(*, version: str = "2026.1") -> ConsentVersion:
    return ConsentVersion(
        version=version,
        effective_at=datetime(2026, 1, 1, tzinfo=UTC),
        notice_text=(
            "DSP AI Indicator processes personal data under India's Digital Personal "
            "Data Protection Act, 2023 for specified purposes only. You may withdraw "
            "non-required consents at any time. Research Mode provides educational "
            "analysis and does not issue SEBI-regulated investment advice."
        ),
        purposes=DEFAULT_PURPOSES,
    )


class InMemoryConsentPort:
    """Process-local consent store — behavioural reference."""

    def __init__(self, policy: ConsentVersion | None = None) -> None:
        self._policy = policy or default_consent_policy()
        self._records: list[ConsentRecord] = []
        self._lock = Lock()

    def current_policy(self) -> ConsentVersion:
        return self._policy

    def record(self, consent: ConsentRecord) -> ConsentRecord:
        with self._lock:
            self._records.append(consent)
        return consent

    def list_for_subject(self, subject_id: str) -> tuple[ConsentRecord, ...]:
        with self._lock:
            return tuple(r for r in self._records if r.subject_id == subject_id)

    def latest_for_purpose(
        self, subject_id: str, purpose_id: str
    ) -> ConsentRecord | None:
        matches = [
            r
            for r in self.list_for_subject(subject_id)
            if r.purpose_id == purpose_id
        ]
        return matches[-1] if matches else None

    def withdraw(
        self, subject_id: str, purpose_id: str, *, policy_version: str
    ) -> ConsentRecord:
        rec = ConsentRecord(
            consent_id=f"cns_{uuid.uuid4().hex[:12]}",
            subject_id=subject_id,
            purpose_id=purpose_id,
            granted=False,
            policy_version=policy_version,
        )
        return self.record(rec)

    def grant(
        self, subject_id: str, purpose_id: str, *, policy_version: str | None = None
    ) -> ConsentRecord:
        rec = ConsentRecord(
            consent_id=f"cns_{uuid.uuid4().hex[:12]}",
            subject_id=subject_id,
            purpose_id=purpose_id,
            granted=True,
            policy_version=policy_version or self._policy.version,
        )
        return self.record(rec)
