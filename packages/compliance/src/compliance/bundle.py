"""Compliance composition bundle (PEP-004)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from compliance.audit import AuditEvent, AuditPort
from compliance.consent import ConsentPort, InMemoryConsentPort
from compliance.disclosure_templates import (
    InMemoryDisclosurePort,
    ResearchModeDisclosureEngine,
)
from compliance.disclosures import DisclosurePort
from compliance.export import ComplianceExportPort, InMemoryComplianceExportPort
from compliance.feature_flags import FeatureFlags, load_feature_flags
from compliance.history_adapters import (
    InMemoryRecommendationHistoryPort,
    InMemoryResearchArchivePort,
)
from compliance.recommendation_history import RecommendationHistoryPort
from compliance.research_archive import ResearchArchivePort
from compliance.retention import (
    AuditRetentionPort,
    InMemoryAuditPort,
    InMemoryAuditRetentionPort,
)

__all__ = ["ComplianceBundle", "CompliancePort"]


@runtime_checkable
class CompliancePort(Protocol):
    """Umbrella compliance façade for composition roots."""

    @property
    def flags(self) -> FeatureFlags: ...

    @property
    def consents(self) -> ConsentPort: ...

    @property
    def disclosures(self) -> DisclosurePort: ...

    @property
    def recommendation_history(self) -> RecommendationHistoryPort: ...

    @property
    def research_archive(self) -> ResearchArchivePort: ...

    @property
    def audit(self) -> AuditPort: ...

    @property
    def audit_retention(self) -> AuditRetentionPort: ...

    @property
    def exports(self) -> ComplianceExportPort: ...


@dataclass
class ComplianceBundle:
    """Reference composition root — offline by default; optional SQL via database=."""

    flags: FeatureFlags
    consents: ConsentPort
    disclosures: DisclosurePort
    recommendation_history: RecommendationHistoryPort
    research_archive: ResearchArchivePort
    audit: AuditPort
    audit_retention: AuditRetentionPort
    exports: ComplianceExportPort
    disclosure_engine: ResearchModeDisclosureEngine

    @classmethod
    def create(
        cls,
        *,
        flags: FeatureFlags | None = None,
        database: Any | None = None,
    ) -> ComplianceBundle:
        resolved_flags = flags if flags is not None else load_feature_flags()
        if database is not None:
            from compliance.persistence import (
                SqlAuditPort,
                SqlConsentPort,
                SqlRecommendationHistoryPort,
                SqlResearchArchivePort,
            )

            consents: ConsentPort = SqlConsentPort(database)
            history: RecommendationHistoryPort = SqlRecommendationHistoryPort(database)
            archive: ResearchArchivePort = SqlResearchArchivePort(database)
            audit: AuditPort = SqlAuditPort(database)
        else:
            consents = InMemoryConsentPort()
            history = InMemoryRecommendationHistoryPort()
            archive = InMemoryResearchArchivePort()
            audit = InMemoryAuditPort()

        retention = InMemoryAuditRetentionPort()
        disclosures = InMemoryDisclosurePort()
        engine = ResearchModeDisclosureEngine(disclosures, flags=resolved_flags)
        exports = InMemoryComplianceExportPort(
            consents=consents,
            history=history,
            archive=archive,
            audit_refs=retention,
        )
        return cls(
            flags=resolved_flags,
            consents=consents,
            disclosures=disclosures,
            recommendation_history=history,
            research_archive=archive,
            audit=audit,
            audit_retention=retention,
            exports=exports,
            disclosure_engine=engine,
        )

    def record_audit(
        self,
        *,
        action: str,
        actor: str,
        resource_ref: str | None = None,
        detail: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_id=f"aud_{uuid.uuid4().hex[:12]}",
            action=action,
            actor=actor,
            occurred_at=datetime.now(tz=UTC),
            resource_ref=resource_ref,
            detail=detail,
        )
        self.audit.record(event)
        self.audit_retention.preserve(event)
        return event
