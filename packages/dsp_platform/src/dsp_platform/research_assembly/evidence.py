"""Primary-source evidence contracts for the canonical research boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse


class EvidenceStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    evidence_id: str
    url: str
    title: str
    publisher: str
    claim: str
    status: EvidenceStatus = EvidenceStatus.UNVERIFIED

    def to_dict(self) -> dict[str, str]:
        return {
            "evidence_id": self.evidence_id,
            "url": self.url,
            "title": self.title,
            "publisher": self.publisher,
            "claim": self.claim,
            "status": self.status.value,
        }


_PRIMARY_HOSTS = frozenset(
    {
        "sec.gov",
        "www.sec.gov",
        "bseindia.com",
        "www.bseindia.com",
        "nseindia.com",
        "www.nseindia.com",
        "investors.",
    }
)


def is_primary_source(url: str, publisher: str = "") -> bool:
    """Return whether a source is an allowed issuer/regulator source."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        return False
    if host in _PRIMARY_HOSTS:
        return True
    return host.startswith("investors.") or publisher.strip().lower() in {
        "sec",
        "sebi",
        "issuer filing",
        "company investor relations",
    }


class EvidenceJudge:
    """Fail-closed gate that preserves provenance and rejects secondary sources."""

    def verify(self, evidence: SourceEvidence) -> SourceEvidence:
        if not evidence.evidence_id.strip() or not evidence.claim.strip():
            return SourceEvidence(
                evidence_id=evidence.evidence_id,
                url=evidence.url,
                title=evidence.title,
                publisher=evidence.publisher,
                claim=evidence.claim,
                status=EvidenceStatus.REJECTED,
            )
        status = (
            EvidenceStatus.VERIFIED
            if is_primary_source(evidence.url, evidence.publisher)
            else EvidenceStatus.REJECTED
        )
        return SourceEvidence(
            evidence_id=evidence.evidence_id,
            url=evidence.url,
            title=evidence.title,
            publisher=evidence.publisher,
            claim=evidence.claim,
            status=status,
        )

    def verify_all(
        self, evidence: tuple[SourceEvidence, ...]
    ) -> tuple[SourceEvidence, ...]:
        return tuple(self.verify(item) for item in evidence)

    def has_verified_primary(self, evidence: tuple[SourceEvidence, ...]) -> bool:
        return any(
            item.status is EvidenceStatus.VERIFIED
            for item in self.verify_all(evidence)
        )


__all__ = ["EvidenceJudge", "EvidenceStatus", "SourceEvidence", "is_primary_source"]
