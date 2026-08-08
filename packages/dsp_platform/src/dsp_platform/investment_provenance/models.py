"""P1-06 — durable investment analysis provenance record."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "INVESTMENT_PROVENANCE_SCHEMA_VERSION",
    "RELEASE_IDENTITY",
    "InvestmentProvenanceRecord",
]

INVESTMENT_PROVENANCE_SCHEMA_VERSION = "1.0.0-p1-06"

# Living product identity — must match scripts/release/release_identity.RC_PROFILE.
RELEASE_IDENTITY: dict[str, str] = {
    "epic": "EPS-003",
    "product_version": "2.0.0-rc.1",
    "channel": "rc",
    "decision": "RELEASE_CANDIDATE",
    "label": "EPS-003 · 2.0.0-rc.1 · rc · RELEASE_CANDIDATE",
}


@dataclass(frozen=True, slots=True)
class InvestmentProvenanceRecord:
    """Append-only investment lineage for one analyse / composition run."""

    analysis_id: str
    created_at: str
    ticker: str
    company: str = ""
    exchange: str | None = None
    correlation_id: str | None = None
    owner_user_id: str | None = None
    org_id: str | None = None
    calculated_at: str | None = None
    source_evidence: dict[str, Any] = field(default_factory=dict)
    financial_validation: dict[str, Any] = field(default_factory=dict)
    valuation: dict[str, Any] = field(default_factory=dict)
    buffett: dict[str, Any] = field(default_factory=dict)
    conclusion: dict[str, Any] = field(default_factory=dict)
    release: dict[str, str] = field(default_factory=lambda: dict(RELEASE_IDENTITY))
    pipeline_version: str | None = None
    platform_version: str | None = None
    package_versions: dict[str, str] = field(default_factory=dict)
    input_fingerprint: str | None = None
    result_fingerprint: str | None = None
    schema_version: str = INVESTMENT_PROVENANCE_SCHEMA_VERSION
    immutable: bool = True
    auditable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "created_at": self.created_at,
            "ticker": self.ticker,
            "company": self.company,
            "exchange": self.exchange,
            "correlation_id": self.correlation_id,
            "owner_user_id": self.owner_user_id,
            "org_id": self.org_id,
            "calculated_at": self.calculated_at or self.created_at,
            "source_evidence": dict(self.source_evidence),
            "financial_validation": dict(self.financial_validation),
            "valuation": dict(self.valuation),
            "buffett": dict(self.buffett),
            "conclusion": dict(self.conclusion),
            "release": dict(self.release),
            "pipeline_version": self.pipeline_version,
            "platform_version": self.platform_version,
            "package_versions": dict(self.package_versions),
            "input_fingerprint": self.input_fingerprint,
            "result_fingerprint": self.result_fingerprint,
            "schema_version": self.schema_version,
            "immutable": self.immutable,
            "auditable": self.auditable,
            "authority": "server",
            "client_overrides_accepted": False,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InvestmentProvenanceRecord:
        return cls(
            analysis_id=str(data["analysis_id"]),
            created_at=str(data["created_at"]),
            ticker=str(data.get("ticker") or ""),
            company=str(data.get("company") or ""),
            exchange=data.get("exchange"),
            correlation_id=data.get("correlation_id"),
            owner_user_id=data.get("owner_user_id"),
            org_id=data.get("org_id"),
            calculated_at=data.get("calculated_at"),
            source_evidence=dict(data.get("source_evidence") or {}),
            financial_validation=dict(data.get("financial_validation") or {}),
            valuation=dict(data.get("valuation") or {}),
            buffett=dict(data.get("buffett") or {}),
            conclusion=dict(data.get("conclusion") or {}),
            release=dict(data.get("release") or dict(RELEASE_IDENTITY)),
            pipeline_version=data.get("pipeline_version"),
            platform_version=data.get("platform_version"),
            package_versions=dict(data.get("package_versions") or {}),
            input_fingerprint=data.get("input_fingerprint"),
            result_fingerprint=data.get("result_fingerprint"),
            schema_version=str(
                data.get("schema_version") or INVESTMENT_PROVENANCE_SCHEMA_VERSION
            ),
            immutable=bool(data.get("immutable", True)),
            auditable=bool(data.get("auditable", True)),
        )
