"""Consent bridge — security ConsentRecordPort → compliance ConsentPort (PEP-004.1).

Canonical DPDP store is ``compliance.ConsentPort``. Identity may record consents
through this adapter without duplicating durable storage.
"""

from __future__ import annotations

from typing import Any, Sequence

from compliance import ConsentRecord as ComplianceConsentRecord
from security_platform import ConsentRecord as SecurityConsentRecord

__all__ = ["ComplianceBackedConsentStore", "consent_source_of_truth"]


consent_source_of_truth = "compliance.ConsentPort"


class ComplianceBackedConsentStore:
    """Adapter implementing security's ConsentRecordPort over compliance ConsentPort."""

    def __init__(self, consent_port: Any) -> None:
        self._port = consent_port

    def record(self, consent: SecurityConsentRecord) -> None:
        policy = self._port.current_policy()
        self._port.record(
            ComplianceConsentRecord(
                consent_id=consent.consent_id,
                subject_id=consent.subject_id,
                purpose_id=consent.purpose,
                granted=consent.granted,
                policy_version=consent.policy_version or policy.version,
                recorded_at=consent.recorded_at,
                channel="identity",
            )
        )

    def list_for_subject(self, subject_id: str) -> Sequence[SecurityConsentRecord]:
        out: list[SecurityConsentRecord] = []
        for row in self._port.list_for_subject(subject_id):
            out.append(
                SecurityConsentRecord(
                    consent_id=row.consent_id,
                    subject_id=row.subject_id,
                    purpose=row.purpose_id,
                    granted=row.granted,
                    recorded_at=row.recorded_at,
                    policy_version=row.policy_version,
                )
            )
        return tuple(out)
