"""EPIC-A005 Institutional Multi-Agent Committee unit tests."""

from __future__ import annotations

from dsp_platform.institutional_committee import (
    AGENT_IDS,
    COMMITTEE_SCHEMA_VERSION,
    UNAVAILABLE_MESSAGE,
    committee_report_from_dict,
    committee_report_to_dict,
    get_agent_registry,
    run_institutional_committee,
)
from dsp_platform.institutional_committee.context import distribute_committee_context
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
                    "summary": "quality",
                }
            ],
            "risk": {"overall": "moderate"},
        }
    return research_object_to_dict(
        build_research_object(
            symbol=symbol,
            object_id=f"ro-ic-{symbol.lower()}",
            created_at=FIXED,
            analysis_payload=analysis,
            data_bundle={
                "identity": {
                    "symbol": symbol,
                    "ticker": symbol,
                    "company_name": f"{symbol} Inc",
                },
                "market_quote": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "financial_statements": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "corporate_actions": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
                "historical_series": {
                    "status": {
                        "available": False,
                        "status": "unavailable",
                        "message": UNAVAILABLE_MESSAGE,
                    },
                    "payload": None,
                },
            },
        )
    )


def test_agent_isolation_and_order() -> None:
    ctx = distribute_committee_context(subject="AAPL", research_object=_ro())
    reviews = get_agent_registry().review_all(ctx)
    assert [r.agent_id for r in reviews] == list(AGENT_IDS)
    # Each review is independent — citations tagged with agent_id
    for review in reviews:
        assert review.citations
        assert all(c.get("agent_id") == review.agent_id for c in review.citations)


def test_context_distribution() -> None:
    ctx = distribute_committee_context(
        subject="msft",
        research_object=_ro("MSFT"),
        report={"report_id": "rpt-1", "generated_at": FIXED},
        diffs=[
            {
                "diff_id": "d1",
                "change_summary": {"identical_content": False},
            }
        ],
    )
    assert ctx.subject == "MSFT"
    assert ctx.source_flags["research_object"] is True
    assert ctx.source_flags["institutional_report"] is True
    assert ctx.source_flags["research_diff"] is True
    assert ctx.section_index["institutional_report"]["available"] is True


def test_consensus_and_minority() -> None:
    result = run_institutional_committee(
        subject="AAPL",
        research_object=_ro(),
        diffs=[
            {
                "diff_id": "d-conflict",
                "created_at": FIXED,
                "change_summary": {"identical_content": False, "fields_changed": 2},
            }
        ],
        monitoring_result={
            "result_id": "mon-1",
            "alerts": [
                {
                    "alert_id": "a1",
                    "severity": "important",
                    "message": "change",
                }
            ],
        },
        report_id="ic-1",
        created_at=FIXED,
    )
    assert result["schema_version"] == COMMITTEE_SCHEMA_VERSION
    assert "stance" in result["consensus"]
    assert result["consensus"]["total_agent_count"] == 8
    # Devil's advocate should be cautionary given conflict signals
    da = next(r for r in result["reviews"] if r["agent_id"] == "devils_advocate")
    assert da["stance"] == "cautionary"
    # Minority opinions present when agents disagree
    assert isinstance(result["minority_opinions"], list)


def test_citations_and_provenance() -> None:
    result = run_institutional_committee(
        subject="IBM",
        research_object=_ro("IBM"),
        report_id="ic-cite",
        created_at=FIXED,
    )
    assert result["citations"]
    assert all(c.get("section") and c.get("path") for c in result["citations"])
    assert result["provenance"]["providers_called"] is False
    assert result["provenance"]["engines_called"] is False
    assert result["provenance"]["calculations_performed"] is False
    assert result["provenance"]["scoring_performed"] is False
    assert result["audit"]["created_at"] == FIXED


def test_unavailable_without_artifacts() -> None:
    result = run_institutional_committee(
        subject="EMPTY",
        report_id="ic-empty",
        created_at=FIXED,
    )
    assert result["consensus"]["stance"] == "unavailable"
    for review in result["reviews"]:
        if review["agent_id"] != "devils_advocate":
            assert review["stance"] == "unavailable"
            assert UNAVAILABLE_MESSAGE in review["summary"] or UNAVAILABLE_MESSAGE in review[
                "findings"
            ]


def test_determinism_and_serde() -> None:
    kwargs = dict(
        subject="META",
        research_object=_ro("META"),
        report={"report_id": "r1", "generated_at": FIXED},
        report_id="ic-det",
        created_at=FIXED,
    )
    a = run_institutional_committee(**kwargs)
    b = run_institutional_committee(**kwargs)
    assert a == b
    restored = committee_report_from_dict(a)
    assert committee_report_to_dict(restored) == a
