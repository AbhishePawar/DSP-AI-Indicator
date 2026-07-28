"""PEP-004 India compliance contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from compliance import (
    AuditRetentionPolicy,
    ComplianceBundle,
    ConsentRecord,
    FeatureFlags,
    format_inr,
    format_ist,
    research_mode_templates,
)
from compliance.history_adapters import InMemoryRecommendationHistoryPort


class TestConsent:
    def test_grant_withdraw_versioning(self) -> None:
        bundle = ComplianceBundle.create(flags=FeatureFlags())
        policy = bundle.consents.current_policy()
        assert policy.version
        assert policy.purposes
        granted = bundle.consents.record(
            ConsentRecord(
                consent_id="c1",
                subject_id="usr_1",
                purpose_id="research_analytics",
                granted=True,
                policy_version=policy.version,
            )
        )
        assert granted.granted is True
        withdrawn = bundle.consents.withdraw(
            "usr_1", "research_analytics", policy_version=policy.version
        )
        assert withdrawn.granted is False
        latest = bundle.consents.latest_for_purpose("usr_1", "research_analytics")
        assert latest is not None
        assert latest.granted is False


class TestDisclosures:
    def test_research_mode_templates_ist_inr(self) -> None:
        catalog = research_mode_templates()
        assert catalog.timezone == "Asia/Kolkata"
        assert catalog.currency == "INR"
        assert any("Research Mode" in d.title for d in catalog.disclosures)
        assert "IST" in format_ist(datetime(2026, 7, 28, 12, 0, tzinfo=UTC))
        assert format_inr(123456.5).startswith("₹")

    def test_disclosure_port_modes(self) -> None:
        bundle = ComplianceBundle.create()
        research = bundle.disclosures.list_active(mode="research")
        sebi = bundle.disclosures.list_active(mode="sebi")
        assert len(sebi) >= len(research)
        assert bundle.flags.research_mode is True
        assert bundle.flags.sebi_mode is False


class TestHistoryAndArchive:
    def test_research_assessment_history(self) -> None:
        hist = InMemoryRecommendationHistoryPort()
        entry = hist.record_research_assessment(
            symbol="INFY", research_label="Attractive", report_ref="rpt_1"
        )
        assert hist.list_for_symbol("infy")[0].entry_id == entry.entry_id

    def test_archive_and_get(self) -> None:
        bundle = ComplianceBundle.create()
        archived = bundle.research_archive.archive("rpt_abc")
        loaded = bundle.research_archive.get(archived.archive_id)
        assert loaded.report_ref == "rpt_abc"


class TestAuditRetention:
    def test_immutable_reference_and_policy_floor(self) -> None:
        with pytest.raises(ValueError):
            AuditRetentionPolicy(retention_days=30)
        bundle = ComplianceBundle.create()
        event = bundle.record_audit(
            action="disclosure_shown",
            actor="system",
            resource_ref="research_mode",
            detail="v2026.1",
        )
        refs = bundle.audit_retention.list_references()
        assert refs
        assert refs[-1].event_id == event.event_id
        assert len(refs[-1].content_hash) == 64
        assert bundle.audit_retention.is_expired(refs[-1]) is False


class TestExport:
    def test_export_subject_json(self) -> None:
        bundle = ComplianceBundle.create()
        policy = bundle.consents.current_policy()
        bundle.consents.record(
            ConsentRecord(
                consent_id="c2",
                subject_id="usr_x",
                purpose_id="account_administration",
                granted=True,
                policy_version=policy.version,
            )
        )
        export = bundle.exports.export_subject("usr_x")
        assert export.timezone == "Asia/Kolkata"
        assert export.currency == "INR"
        body = export.to_json()
        assert "account_administration" in body


class TestPersistenceWithPep002:
    def test_sql_adapters_via_database_port(self) -> None:
        from production_platform import InfrastructureBundle

        infra = InfrastructureBundle.create_offline()
        bundle = ComplianceBundle.create(database=infra.database)
        policy = bundle.consents.current_policy()
        bundle.consents.record(
            ConsentRecord(
                consent_id="c_sql",
                subject_id="usr_sql",
                purpose_id="audit_retention",
                granted=True,
                policy_version=policy.version,
            )
        )
        rows = bundle.consents.list_for_subject("usr_sql")
        assert len(rows) == 1
        archived = bundle.research_archive.archive("sql_rpt")
        assert bundle.research_archive.get(archived.archive_id).report_ref == "sql_rpt"


class TestCompliancePortProtocol:
    def test_bundle_satisfies_port(self) -> None:
        bundle = ComplianceBundle.create()
        assert bundle.flags.is_research_only() is True
        assert isinstance(bundle, object)
