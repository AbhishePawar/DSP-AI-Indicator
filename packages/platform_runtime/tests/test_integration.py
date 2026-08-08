"""PEP-004.1 enterprise integration tests."""

from __future__ import annotations

from platform_runtime import EnterprisePlatform, consent_source_of_truth


class TestEnterpriseComposition:
    def test_offline_composition_ready(self) -> None:
        platform = EnterprisePlatform.create_offline()
        validation = platform.validate_startup()
        assert validation.ok, validation.errors
        report = platform.readiness()
        assert report.ready is True
        assert any(c.name == "consent_alignment" and c.ok for c in report.checks)
        assert any(c.name == "research_mode_default" and c.ok for c in report.checks)
        assert any(c.name == "readiness" and c.ok for c in report.checks)

    def test_consent_alignment_identity_to_compliance(self) -> None:
        platform = EnterprisePlatform.create_offline()
        assert platform.consent_source_of_truth == consent_source_of_truth
        platform.security.identity.record_consent(
            subject_id="usr_admin",
            purpose="research_analytics",
            granted=True,
            policy_version=platform.compliance.consents.current_policy().version,
        )
        rows = platform.compliance.consents.list_for_subject("usr_admin")
        assert any(r.purpose_id == "research_analytics" and r.granted for r in rows)
        # Same store visible via identity bridge list
        bridged = platform.security.identity._consents.list_for_subject("usr_admin")  # noqa: SLF001
        assert any(r.purpose == "research_analytics" for r in bridged)

    def test_infra_security_session_and_obs_metrics(self) -> None:
        platform = EnterprisePlatform.create_offline()
        pair = platform.security.identity.authenticate("admin", "StrongPass12")
        assert pair.access_token
        assert platform.infrastructure.session.get(pair.session_id) is not None
        platform.observability.metrics.incr("pep0041_smoke")
        text = platform.production.render_prometheus()
        assert "dsp_up 1" in text
        platform.observability.audit.emit(
            action="integration_smoke",
            subject="usr_admin",
            success=True,
        )
        assert platform.observability.audit.list_events()

    def test_compliance_disclosures_and_export(self) -> None:
        platform = EnterprisePlatform.create_offline()
        disclosures = platform.compliance.disclosures.list_active(mode="research")
        assert disclosures
        export = platform.compliance.exports.export_subject("usr_admin")
        assert export.timezone == "Asia/Kolkata"
        assert "INR" == export.currency

    def test_no_sebi_mode_by_default(self) -> None:
        platform = EnterprisePlatform.create_offline()
        assert platform.compliance.flags.sebi_mode is False
        assert platform.compliance.flags.is_research_only() is True

    def test_from_environment_offline(self) -> None:
        platform = EnterprisePlatform.from_environment(force_offline=True)
        validation = platform.validate_startup()
        assert validation.ok, validation.errors
        diag = platform.diagnostics()
        assert diag["infrastructure"]["database"] == "InMemoryDatabasePort"
        assert "probes" in diag["infrastructure"]
        assert any(c.name == "database" and c.ok for c in platform.readiness().checks)
        assert any(c.name == "redis" and c.ok for c in platform.readiness().checks)
