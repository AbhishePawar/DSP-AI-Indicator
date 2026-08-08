"""P1-06 — investment provenance builder / store unit tests."""

from __future__ import annotations

from dsp_platform.investment_provenance import (
    DatabaseInvestmentProvenanceStore,
    build_investment_provenance,
    canonical_fingerprint,
    redact_secrets,
    source_evidence_from_trace,
)
from production_platform import InMemoryDatabasePort


def test_source_evidence_unavailable_without_trace() -> None:
    evidence = source_evidence_from_trace(None)
    assert evidence["authenticated"] is False
    assert evidence["status"] == "unavailable"
    assert evidence["status"] != "live"


def test_source_evidence_from_authenticated_trace() -> None:
    evidence = source_evidence_from_trace(
        {
            "authenticated": True,
            "ticker": "ACM",
            "reporting_currency": "USD",
            "period_kind": "annual",
            "statement_basis": "as_reported",
            "unit_scale": "millions",
            "current_market_price": 70.0,
            "shares_outstanding": 100.0,
            "statement_provenance": {
                "provider": "fixture_provider",
                "retrieved_at": "2026-08-08T00:00:00Z",
                "api_key": "should-redact",
            },
            "quote_provenance": {
                "provider": "quote_provider",
                "retrieved_at": "2026-08-08T00:00:00Z",
            },
        }
    )
    assert evidence["authenticated"] is True
    assert evidence["statement_provider"] == "fixture_provider"
    assert evidence["statement_provenance"]["api_key"] == "[REDACTED]"


def test_append_only_rejects_duplicate_analysis_id() -> None:
    db = InMemoryDatabasePort()
    store = DatabaseInvestmentProvenanceStore(db)
    record = build_investment_provenance(
        public_payload={
            "ok": True,
            "metadata": {"pipeline_version": "1.0.0"},
            "stage_summaries": [],
            "recommendation_summary": {"decision": "hold"},
            "committee_summary": {},
            "buffett_authority": {},
        },
        ticker="ACM",
        analysis_id="dup-1",
        created_at="2026-08-08T00:00:00+00:00",
    )
    store.append(record)
    try:
        store.append(record)
        raised = False
    except Exception:
        raised = True
    assert raised is True


def test_backup_restore_simulation_retains_provenance() -> None:
    """G11-style: process state wiped; DatabasePort rows remain readable."""
    db = InMemoryDatabasePort()
    worker_a = DatabaseInvestmentProvenanceStore(db)
    record = build_investment_provenance(
        public_payload={
            "ok": True,
            "metadata": {"pipeline_version": "1.0.0", "package_versions": {}},
            "stage_summaries": [
                {
                    "stage": "business_quality_aggregator",
                    "status": "succeeded",
                    "has_result": True,
                    "score": 76,
                    "label": "good",
                }
            ],
            "recommendation_summary": {"decision": "buy", "score": 70},
            "committee_summary": {"decision": "accumulate"},
            "buffett_authority": {
                "overall_score": 76,
                "overall_label": "good",
                "recommendation": "buy",
                "factors": {},
            },
        },
        ticker="ACM",
        analysis_id="restore-1",
        created_at="2026-08-08T00:00:00+00:00",
    )
    worker_a.append(record)

    # Simulate restore onto a fresh worker process sharing the same DB bytes.
    worker_b = DatabaseInvestmentProvenanceStore(db)
    restored = worker_b.get("restore-1")
    assert restored is not None
    assert restored.conclusion["recommendation"] == "buy"
    assert restored.buffett["overall_score"] == 76
    assert restored.release["epic"] == "EPS-003"


def test_redact_and_fingerprint_stable() -> None:
    payload = {"a": 1, "nested": {"b": 2}}
    assert canonical_fingerprint(payload) == canonical_fingerprint(
        {"nested": {"b": 2}, "a": 1}
    )
    assert redact_secrets({"jwt_token": "x", "keep": True})["jwt_token"] == "[REDACTED]"
