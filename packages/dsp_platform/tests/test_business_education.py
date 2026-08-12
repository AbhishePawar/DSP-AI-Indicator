"""Educational Business & Buffett analysis — isolation & safety tests."""

from __future__ import annotations

import copy

import pytest

from dsp_platform.business_education import (
    UNAVAILABLE_MESSAGE,
    build_business_education_report,
    business_education_schema,
)
from dsp_platform.business_education.business_types import (
    detect_business_type,
    preferred_metrics,
)
from dsp_platform.business_education.firewall import (
    FORBIDDEN_OUTPUT_KEYS,
    ValuationFirewallError,
    assert_report_has_no_forbidden_outputs,
)
from dsp_platform.business_education.models import SECTION_ORDER


def _payload(**kwargs):
    base = {
        "ticker": "AAPL",
        "company": "Apple Inc",
        "exchange": "NASDAQ",
        "valuation_signals": {
            "intrinsic_value_per_share": 180.0,
            "current_market_price": 190.0,
            "confidence": 0.7,
        },
        "recommendation": {"action": "hold", "confidence": 0.6},
        "stage_summaries": [
            {
                "stage": "financial",
                "status": "succeeded",
                "score": 72,
                "label": "Solid",
                "confidence": 0.7,
                "warnings": ["Client concentration elevated"],
            },
            {
                "stage": "economic_moat",
                "status": "succeeded",
                "score": 80,
                "label": "Wide",
                "decision": "durable",
                "confidence": 0.75,
                "warnings": [],
            },
            {
                "stage": "management_quality",
                "status": "succeeded",
                "score": 70,
                "label": "Capable",
                "confidence": 0.7,
                "metrics": [{"label": "Capital Allocation", "value": "Rational"}],
                "warnings": [],
            },
            {
                "stage": "financial_strength",
                "status": "succeeded",
                "score": 78,
                "label": "Strong",
                "metrics": [
                    {"label": "Debt", "value": "Low"},
                    {"label": "Liquidity", "value": "Adequate"},
                    {"label": "Cash Flow", "value": "Positive"},
                ],
                "warnings": [],
            },
            {
                "stage": "earnings_quality",
                "status": "succeeded",
                "score": 74,
                "label": "Consistent",
                "metrics": [
                    {"label": "Consistency", "value": "High"},
                    {"label": "Cash Conversion", "value": "Strong"},
                ],
                "warnings": [],
            },
            {
                "stage": "growth_quality",
                "status": "succeeded",
                "score": 68,
                "label": "Moderate",
                "metrics": [
                    {"label": "Revenue Growth", "value": "8%"},
                    {"label": "Profit Growth", "value": "6%"},
                    {"label": "Reinvestment", "value": "Ongoing"},
                ],
                "warnings": [],
            },
            {
                "stage": "business_quality",
                "status": "succeeded",
                "score": 76,
                "label": "Good",
                "warnings": [],
            },
        ],
    }
    base.update(kwargs)
    return base


def test_schema_declares_firewall():
    schema = business_education_schema()
    assert schema["writes_valuation"] is False
    assert schema["writes_buffett_score"] is False
    assert len(schema["sections"]) == 12


def test_generates_twelve_sections():
    report = build_business_education_report(_payload(), symbol="AAPL")
    assert len(report["sections"]) == 12
    assert [s["id"] for s in report["sections"]] == list(SECTION_ORDER)
    assert report["title"] == "Business & Buffett Analysis"
    assert report["writes_valuation"] is False
    assert report["writes_buffett_score"] is False


def test_missing_data_uses_unavailable_message():
    report = build_business_education_report(
        {"stage_summaries": []}, symbol="XYZ", company="Unknown"
    )
    strengths = next(s for s in report["sections"] if s["id"] == "the_real_strengths")
    assert any(UNAVAILABLE_MESSAGE in c["text"] for c in strengths["claims"])


def test_bank_metric_selection():
    assert detect_business_type(industry="Commercial banking") == "bank"
    assert "nim" in preferred_metrics("bank")
    assert "gnpa" in preferred_metrics("bank")
    report = build_business_education_report(
        _payload(),
        symbol="HDFCBANK",
        company="HDFC Bank",
        industry="Commercial banking",
    )
    assert report["business_type"] == "bank"
    assert "nim" in report["preferred_metrics"]


def test_it_saas_metric_selection():
    assert detect_business_type(industry="IT services software") == "it_saas"
    assert "arr" in preferred_metrics("it_saas")


def test_ai_cannot_overwrite_valuation_signals():
    payload = _payload()
    before = copy.deepcopy(payload["valuation_signals"])
    report = build_business_education_report(payload)
    assert payload["valuation_signals"] == before
    assert report["writes_valuation"] is False
    # Report must not invent IV / price / MoS keys
    with pytest.raises(ValuationFirewallError):
        assert_report_has_no_forbidden_outputs(
            {**report, "intrinsic_value": 999}
        )


def test_ai_cannot_overwrite_buffett_score_or_create_prices():
    report = build_business_education_report(_payload())
    for key in FORBIDDEN_OUTPUT_KEYS:
        assert key not in report
    assert report["writes_buffett_score"] is False


def test_report_has_no_forbidden_output_keys():
    report = build_business_education_report(_payload())
    assert_report_has_no_forbidden_outputs(report)


def test_unavailable_data_produces_explicit_uncertainty():
    report = build_business_education_report(
        {"stage_summaries": [], "source": "production"},
        symbol="ZZZ",
    )
    dq = next(
        s for s in report["sections"] if s["id"] == "data_quality_and_uncertainty"
    )
    assert any("Data unavailable" in b or "unavailable" in b.lower() for b in dq["bullets"])


def test_demo_seed_not_presented_as_authoritative():
    report = build_business_education_report(
        _payload(source="demo seed fixture"),
        symbol="ACM",
        company="Demo Co",
    )
    assert report["provenance"]["demo_contaminated"] is True
    fh = next(s for s in report["sections"] if s["id"] == "financial_health")
    assert fh["demo_contaminated"] is True
    # Contaminated numeric stage metrics should not be presented as available facts
    available_metrics = [c for c in fh["claims"] if c["kind"] == "CALCULATED_METRIC" and c["available"]]
    assert available_metrics == []


def test_educational_conclusion_has_no_investment_verdict():
    report = build_business_education_report(_payload())
    conclusion = next(
        s for s in report["sections"] if s["id"] == "educational_conclusion"
    )
    text = conclusion["summary"].lower()
    for token in ("buy", "sell", "hold", "strong buy", "price target"):
        # word-boundary style check
        assert f" {token} " not in f" {text} "
    assert conclusion.get("investment_verdict") is None


def test_buffett_checklist_does_not_compute_score():
    report = build_business_education_report(_payload())
    checklist_sec = next(
        s for s in report["sections"] if s["id"] == "the_buffett_checklist"
    )
    assert checklist_sec["buffett_score_computed"] is False
    assert len(checklist_sec["checklist"]) == 9


def test_three_key_risks_present():
    report = build_business_education_report(_payload())
    risks = next(
        s for s in report["sections"] if s["id"] == "key_risks_to_understand"
    )
    assert len(risks["risks"]) == 3


def test_provenance_retained_on_claims():
    report = build_business_education_report(_payload())
    for sec in report["sections"]:
        for c in sec["claims"]:
            assert "kind" in c
            assert "source" in c or c["kind"] == "UNAVAILABLE"
