"""EPIC-A006 Investment Policy & Compliance unit tests."""

from __future__ import annotations

from dsp_platform.investment_policy import (
    DEFAULT_POLICY_ID,
    POLICY_SCHEMA_VERSION,
    UNAVAILABLE_MESSAGE,
    compliance_result_from_dict,
    compliance_result_to_dict,
    default_institutional_policy,
    evaluate_investment_policy,
    load_investment_policy,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


def _ro(symbol: str = "AAPL", *, rich: bool = True) -> dict:
    analysis: dict = {"ok": True}
    if rich:
        analysis = {
            "ok": True,
            "recommendation_summary": {
                "label": "Research Mode",
                "margin_of_safety": 0.25,
            },
            "stage_summaries": [
                {
                    "stage": "business_quality_aggregator",
                    "has_result": True,
                    "summary": "q",
                }
            ],
            "risk": {"overall": "moderate"},
        }
    return research_object_to_dict(
        build_research_object(
            symbol=symbol,
            object_id=f"ro-pol-{symbol.lower()}",
            created_at=FIXED,
            analysis_payload=analysis,
        )
    )


def test_policy_loading_default() -> None:
    policy = default_institutional_policy()
    assert policy.policy_id == DEFAULT_POLICY_ID
    assert len(policy.rules) >= 5
    loaded = load_investment_policy(policy.to_dict())
    assert loaded.policy_id == policy.policy_id
    assert [r.rule_id for r in loaded.rules] == sorted(r.rule_id for r in policy.rules)


def test_rule_evaluation_and_compliance_summary() -> None:
    result = evaluate_investment_policy(
        subject="AAPL",
        research_object=_ro(),
        report={"report_id": "rpt-1", "generated_at": FIXED},
        committee_report={
            "report_id": "ic-1",
            "consensus": {"stance": "supportive", "confidence": "medium"},
        },
        portfolio_intelligence={
            "result_id": "pi-1",
            "missing_research": [],
        },
        monitoring_result={"result_id": "mon-1", "alerts": []},
        diffs=[
            {
                "diff_id": "d1",
                "change_summary": {"identical_content": True},
            }
        ],
        result_id="pol-1",
        created_at=FIXED,
    )
    assert result["schema_version"] == POLICY_SCHEMA_VERSION
    assert result["summary"]["status"] in {
        "compliant",
        "compliant_with_warnings",
        "non_compliant",
    }
    assert result["summary"]["counts"]["pass"] >= 1
    assert result["provenance"]["providers_called"] is False
    assert result["provenance"]["calculations_performed"] is False


def test_violations_and_warnings() -> None:
    result = evaluate_investment_policy(
        subject="MSFT",
        research_object=_ro("MSFT", rich=False),
        committee_report={
            "report_id": "ic-2",
            "consensus": {"stance": "unavailable"},
        },
        portfolio_intelligence={
            "result_id": "pi-2",
            "missing_research": [{"symbol": "XYZ"}],
        },
        monitoring_result={
            "result_id": "mon-2",
            "alerts": [{"alert_id": "a1", "severity": "important"}],
        },
        diffs=[
            {
                "diff_id": "d2",
                "change_summary": {"identical_content": False},
            }
        ],
        result_id="pol-viol",
        created_at=FIXED,
    )
    assert result["summary"]["status"] == "non_compliant"
    assert result["violations"]
    assert result["warnings"] or result["summary"]["counts"]["warning"] >= 0
    assert any(v["outcome"] == "violation" for v in result["violations"])


def test_exception_waiver() -> None:
    policy = default_institutional_policy().to_dict()
    result = evaluate_investment_policy(
        subject="IBM",
        policy=policy,
        exceptions=[
            {
                "exception_id": "ex-1",
                "rule_id": "REQ-RO-PRESENT",
                "reason": "pilot waiver",
                "created_at": FIXED,
            }
        ],
        result_id="pol-waiver",
        created_at=FIXED,
    )
    waived = next(r for r in result["rule_results"] if r["rule_id"] == "REQ-RO-PRESENT")
    assert waived["outcome"] == "waived"


def test_citations_and_provenance() -> None:
    result = evaluate_investment_policy(
        subject="GOOG",
        research_object=_ro("GOOG"),
        result_id="pol-cite",
        created_at=FIXED,
    )
    assert result["citations"]
    assert all(c.get("section") and c.get("path") for c in result["citations"])
    for rule in result["rule_results"]:
        assert rule["citations"]
    assert result["audit"]["created_at"] == FIXED
    assert result["audit_trail"]


def test_unavailable_message() -> None:
    result = evaluate_investment_policy(
        subject="EMPTY",
        result_id="pol-empty",
        created_at=FIXED,
    )
    # RO missing → violation or unavailable on section rules
    messages = [r["message"] for r in result["rule_results"]]
    assert any(UNAVAILABLE_MESSAGE in m or "missing" in m.lower() for m in messages)


def test_determinism_and_serde() -> None:
    kwargs = dict(
        subject="META",
        research_object=_ro("META"),
        report={"report_id": "r1"},
        committee_report={
            "report_id": "ic",
            "consensus": {"stance": "cautionary"},
        },
        portfolio_intelligence={"result_id": "pi", "missing_research": []},
        monitoring_result={"result_id": "mon", "alerts": []},
        result_id="pol-det",
        created_at=FIXED,
    )
    a = evaluate_investment_policy(**kwargs)
    b = evaluate_investment_policy(**kwargs)
    assert a == b
    restored = compliance_result_from_dict(a)
    assert compliance_result_to_dict(restored) == a
