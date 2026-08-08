"""EPIC-A004 Institutional Decision Workspace unit tests."""

from __future__ import annotations

from dsp_platform.decision_workspace import (
    PANEL_NAMES,
    UNAVAILABLE_MESSAGE,
    WORKSPACE_SCHEMA_VERSION,
    build_decision_workspace,
    workspace_result_from_dict,
    workspace_result_to_dict,
)
from dsp_platform.research_object import build_research_object, research_object_to_dict

FIXED = "2026-07-28T12:00:00+00:00"


def _ro(symbol: str = "AAPL") -> dict:
    return research_object_to_dict(
        build_research_object(
            symbol=symbol,
            object_id=f"ro-ws-{symbol.lower()}",
            created_at=FIXED,
            analysis_payload={
                "ok": True,
                "recommendation_summary": {
                    "label": "Research Mode",
                    "margin_of_safety": 0.2,
                },
            },
        )
    )


def test_company_workspace_aggregation() -> None:
    result = build_decision_workspace(
        kind="company",
        subject="AAPL",
        research_object=_ro(),
        report={"report_id": "rpt-1", "generated_at": FIXED, "schema_version": "1.0.0"},
        snapshots=[
            {
                "snapshot_id": "snap-1",
                "kind": "research_object",
                "archived_at": FIXED,
                "version": {"lineage_id": "lin-1"},
            }
        ],
        diffs=[
            {
                "diff_id": "diff-1",
                "created_at": FIXED,
                "left_snapshot_id": "snap-0",
                "right_snapshot_id": "snap-1",
                "change_summary": {
                    "identical_content": False,
                    "fields_changed": 1,
                },
            }
        ],
        workspace_id="ws-1",
        created_at=FIXED,
    )
    assert result["schema_version"] == WORKSPACE_SCHEMA_VERSION
    assert result["kind"] == "company"
    assert result["subject"] == "AAPL"
    assert [p["name"] for p in result["panels"]] == list(PANEL_NAMES)
    by_name = {p["name"]: p for p in result["panels"]}
    assert by_name["research"]["available"] is True
    assert by_name["report"]["available"] is True
    assert by_name["snapshot_history"]["available"] is True
    assert by_name["diff_history"]["available"] is True
    assert result["provenance"]["providers_called"] is False
    assert result["provenance"]["calculations_performed"] is False


def test_timeline_and_alerts() -> None:
    result = build_decision_workspace(
        kind="company",
        subject="MSFT",
        research_object=_ro("MSFT"),
        monitoring_result={
            "result_id": "mon-1",
            "created_at": FIXED,
            "alerts": [
                {
                    "alert_id": "a1",
                    "severity": "important",
                    "subject": "MSFT",
                    "alert_type": "research_change",
                    "message": "changed",
                    "citations": [
                        {
                            "section": "recommendation",
                            "path": "x",
                            "source_kind": "research_diff",
                        }
                    ],
                }
            ],
            "audit": {"alert_count": 1},
        },
        workspace_id="ws-tl",
        created_at=FIXED,
    )
    assert len(result["timeline"]) >= 2
    alerts = next(p for p in result["panels"] if p["name"] == "active_alerts")
    assert alerts["available"] is True
    assert alerts["summary"]["active_count"] == 1


def test_portfolio_and_copilot_integration() -> None:
    result = build_decision_workspace(
        kind="portfolio",
        subject="pf-1",
        portfolio_intelligence={
            "result_id": "pi-1",
            "created_at": FIXED,
            "portfolio_summary": {
                "holding_count": 2,
                "linked_research_count": 1,
                "missing_research_count": 1,
            },
        },
        copilot_response={
            "response_id": "cp-1",
            "answer": "Data unavailable.",
            "unavailable": True,
            "citations": [],
        },
        workspace_id="ws-pf",
        created_at=FIXED,
    )
    by_name = {p["name"]: p for p in result["panels"]}
    assert by_name["portfolio"]["available"] is True
    assert by_name["copilot"]["available"] is True
    assert by_name["research"]["available"] is False
    assert by_name["research"]["message"] == UNAVAILABLE_MESSAGE


def test_watchlist_workspace() -> None:
    result = build_decision_workspace(
        kind="watchlist",
        subject="wl-1",
        portfolio_intelligence={
            "result_id": "pi-wl",
            "watchlist_summary": {"symbol_count": 3},
            "portfolio_summary": {},
        },
        workspace_id="ws-wl",
        created_at=FIXED,
    )
    assert result["kind"] == "watchlist"
    assert any(p["name"] == "portfolio" and p["available"] for p in result["panels"])


def test_citations_and_provenance() -> None:
    result = build_decision_workspace(
        kind="company",
        subject="IBM",
        research_object=_ro("IBM"),
        workspace_id="ws-cite",
        created_at=FIXED,
    )
    assert result["citations"]
    assert all(c.get("section") and c.get("path") for c in result["citations"])
    for panel in result["panels"]:
        assert panel["citations"]
    assert result["provenance"]["source"] == "decision_workspace"
    assert result["audit"]["created_at"] == FIXED


def test_determinism_and_serde() -> None:
    kwargs = dict(
        kind="company",
        subject="META",
        research_object=_ro("META"),
        report={"report_id": "r-d", "generated_at": FIXED},
        snapshots=[{"snapshot_id": "s-d", "archived_at": FIXED, "kind": "research_object"}],
        workspace_id="ws-det",
        created_at=FIXED,
    )
    a = build_decision_workspace(**kwargs)
    b = build_decision_workspace(**kwargs)
    assert a == b
    restored = workspace_result_from_dict(a)
    assert workspace_result_to_dict(restored) == a


def test_empty_sources_unavailable_panels() -> None:
    result = build_decision_workspace(
        kind="company",
        subject="EMPTY",
        workspace_id="ws-empty",
        created_at=FIXED,
    )
    by_name = {p["name"]: p for p in result["panels"]}
    assert by_name["research"]["message"] == UNAVAILABLE_MESSAGE
    assert by_name["audit"]["available"] is True
    assert result["timeline"][0]["available"] is False
