"""EPIC-A007 Institutional Workflow & Approval unit tests."""

from __future__ import annotations

import pytest

from dsp_platform.institutional_workflow import (
    DEFAULT_TEMPLATE_ID,
    WORKFLOW_SCHEMA_VERSION,
    ALLOWED_TRANSITIONS,
    apply_workflow_action,
    get_workflow_template,
    list_workflow_templates,
    reset_workflow_registry_for_tests,
    workflow_result_from_dict,
    workflow_result_to_dict,
)

FIXED = "2026-07-28T12:00:00+00:00"


@pytest.fixture(autouse=True)
def _reset() -> None:
    reset_workflow_registry_for_tests()
    yield
    reset_workflow_registry_for_tests()


def _create(**extra: object) -> dict:
    kwargs = dict(
        action="create",
        subject="AAPL",
        template_id=DEFAULT_TEMPLATE_ID,
        workflow_id="wf-1",
        artifact_refs={
            "research_object_id": "ro-1",
            "report_id": "rpt-1",
            "committee_report_id": "ic-1",
            "compliance_result_id": "pol-1",
        },
        reviewers=[{"reviewer_id": "u1", "role": "analyst"}],
        actor_id="system",
        result_id="res-create",
        created_at=FIXED,
    )
    kwargs.update(extra)
    return apply_workflow_action(**kwargs)


def test_workflow_lifecycle_and_transitions() -> None:
    created = _create()
    assert created["schema_version"] == WORKFLOW_SCHEMA_VERSION
    assert created["workflow"]["stage"] == "draft"
    assert created["provenance"]["research_mutated"] is False

    stages = [
        ("review", "ap-1", "ev-1"),
        ("compliance_review", "ap-2", "ev-2"),
        ("committee_review", "ap-3", "ev-3"),
        ("approved", "ap-4", "ev-4"),
        ("published", "ap-5", "ev-5"),
    ]
    current = created
    for stage, ap, ev in stages:
        current = apply_workflow_action(
            action="transition",
            workflow_id="wf-1",
            to_stage=stage,
            actor_id="u1",
            approval_id=ap,
            event_id=ev,
            result_id=f"res-{stage}",
            created_at=FIXED,
        )
        assert current["workflow"]["stage"] == stage

    assert len(current["workflow"]["decision_history"]) == 5
    assert len(current["workflow"]["approvals"]) == 5
    assert current["workflow"]["audit_trail"]


def test_reject_path() -> None:
    _create(workflow_id="wf-rej", result_id="res-rej-c")
    apply_workflow_action(
        action="transition",
        workflow_id="wf-rej",
        to_stage="review",
        actor_id="u1",
        approval_id="ap-r1",
        event_id="ev-r1",
        created_at=FIXED,
        result_id="res-rej-1",
    )
    rejected = apply_workflow_action(
        action="transition",
        workflow_id="wf-rej",
        to_stage="rejected",
        actor_id="u2",
        reason="incomplete evidence",
        approval_id="ap-r2",
        event_id="ev-r2",
        created_at=FIXED,
        result_id="res-rej-2",
    )
    assert rejected["workflow"]["stage"] == "rejected"
    with pytest.raises(ValueError, match="terminal"):
        apply_workflow_action(
            action="transition",
            workflow_id="wf-rej",
            to_stage="review",
            actor_id="u1",
            created_at=FIXED,
        )


def test_invalid_transition() -> None:
    _create(workflow_id="wf-bad", result_id="res-bad")
    with pytest.raises(ValueError, match="not allowed"):
        apply_workflow_action(
            action="transition",
            workflow_id="wf-bad",
            to_stage="approved",
            actor_id="u1",
            created_at=FIXED,
        )


def test_comments_and_approval_history() -> None:
    _create(workflow_id="wf-c", result_id="res-c")
    commented = apply_workflow_action(
        action="comment",
        workflow_id="wf-c",
        author_id="u1",
        body="Looks complete.",
        comment_id="c-1",
        created_at=FIXED,
        result_id="res-comment",
    )
    assert commented["workflow"]["comments"][0]["body"] == "Looks complete."
    assert any(
        e["event"] == "comment_added" for e in commented["workflow"]["audit_trail"]
    )


def test_citations_and_provenance() -> None:
    result = _create()
    assert result["citations"]
    assert any(
        c["source_kind"] == "research_object" and c["available"]
        for c in result["citations"]
    )
    assert result["provenance"]["providers_called"] is False
    assert result["provenance"]["engines_called"] is False
    assert result["audit"]["created_at"] == FIXED


def test_determinism_and_serde() -> None:
    a = _create(workflow_id="wf-det", result_id="res-det")
    g1 = apply_workflow_action(
        action="get", workflow_id="wf-det", result_id="res-get", created_at=FIXED
    )
    g2 = apply_workflow_action(
        action="get", workflow_id="wf-det", result_id="res-get", created_at=FIXED
    )
    assert g1 == g2
    restored = workflow_result_from_dict(a)
    assert workflow_result_to_dict(restored)["workflow"]["workflow_id"] == "wf-det"


def test_missing_workflow_unavailable() -> None:
    with pytest.raises(ValueError, match="Data unavailable"):
        apply_workflow_action(action="get", workflow_id="missing", created_at=FIXED)


def test_assign_reviewer() -> None:
    _create(workflow_id="wf-asg", result_id="res-asg-c", reviewers=[])
    assigned = apply_workflow_action(
        action="assign_reviewer",
        workflow_id="wf-asg",
        reviewer_id="comp-1",
        role="compliance_officer",
        display_name="Compliance",
        actor_id="admin",
        created_at=FIXED,
        result_id="res-asg",
    )
    assert any(r["reviewer_id"] == "comp-1" for r in assigned["workflow"]["reviewers"])
    assert any(
        e["event"] == "reviewer_assigned" for e in assigned["workflow"]["audit_trail"]
    )
    with pytest.raises(ValueError, match="duplicate"):
        apply_workflow_action(
            action="assign_reviewer",
            workflow_id="wf-asg",
            reviewer_id="comp-1",
            created_at=FIXED,
        )


def test_history_action() -> None:
    _create(workflow_id="wf-hist", result_id="res-hist-c")
    apply_workflow_action(
        action="transition",
        workflow_id="wf-hist",
        to_stage="review",
        actor_id="u1",
        approval_id="ap-h1",
        event_id="ev-h1",
        created_at=FIXED,
        result_id="res-hist-t",
    )
    hist = apply_workflow_action(
        action="history",
        workflow_id="wf-hist",
        result_id="res-hist",
        created_at=FIXED,
    )
    assert hist["action"] == "history"
    assert hist["audit"]["decision_count"] == 1
    assert hist["workflow"]["decision_history"]


def test_approve_convenience_from_committee() -> None:
    _create(workflow_id="wf-ap", result_id="res-ap-c")
    for stage, ap, ev in [
        ("review", "a1", "e1"),
        ("compliance_review", "a2", "e2"),
        ("committee_review", "a3", "e3"),
    ]:
        apply_workflow_action(
            action="transition",
            workflow_id="wf-ap",
            to_stage=stage,
            actor_id="u1",
            approval_id=ap,
            event_id=ev,
            created_at=FIXED,
            result_id=f"res-{stage}",
        )
    approved = apply_workflow_action(
        action="approve",
        workflow_id="wf-ap",
        actor_id="committee-1",
        approval_id="a4",
        event_id="e4",
        created_at=FIXED,
        result_id="res-approve",
    )
    assert approved["workflow"]["stage"] == "approved"


def test_reject_convenience() -> None:
    _create(workflow_id="wf-rj2", result_id="res-rj2-c")
    apply_workflow_action(
        action="transition",
        workflow_id="wf-rj2",
        to_stage="review",
        actor_id="u1",
        approval_id="ar1",
        event_id="er1",
        created_at=FIXED,
        result_id="res-rj2-t",
    )
    rejected = apply_workflow_action(
        action="reject",
        workflow_id="wf-rj2",
        actor_id="u2",
        reason="policy gap",
        approval_id="ar2",
        event_id="er2",
        created_at=FIXED,
        result_id="res-rj2-r",
    )
    assert rejected["workflow"]["stage"] == "rejected"
    assert rejected["workflow"]["approvals"][-1]["decision"] == "reject"


def test_templates_registry() -> None:
    templates = list_workflow_templates()
    assert templates
    assert templates[0]["template_id"] == DEFAULT_TEMPLATE_ID
    tpl = get_workflow_template(DEFAULT_TEMPLATE_ID)
    assert "draft" in tpl["stages"]
    assert ALLOWED_TRANSITIONS["draft"] == ("review",)


def test_subject_required() -> None:
    with pytest.raises(ValueError, match="subject"):
        apply_workflow_action(
            action="create",
            subject="",
            workflow_id="wf-empty",
            created_at=FIXED,
        )


def test_comment_body_required() -> None:
    _create(workflow_id="wf-cb", result_id="res-cb")
    with pytest.raises(ValueError, match="comment body"):
        apply_workflow_action(
            action="comment",
            workflow_id="wf-cb",
            author_id="u1",
            body="  ",
            created_at=FIXED,
        )


def test_audit_trail_immutable_append() -> None:
    _create(workflow_id="wf-au", result_id="res-au")
    first = apply_workflow_action(
        action="transition",
        workflow_id="wf-au",
        to_stage="review",
        actor_id="u1",
        approval_id="au1",
        event_id="eu1",
        created_at=FIXED,
        result_id="res-au-t",
    )
    n = len(first["workflow"]["audit_trail"])
    second = apply_workflow_action(
        action="comment",
        workflow_id="wf-au",
        author_id="u1",
        body="note",
        comment_id="c-au",
        created_at=FIXED,
        result_id="res-au-c",
    )
    assert len(second["workflow"]["audit_trail"]) == n + 1
    assert second["workflow"]["audit_trail"][:n] == first["workflow"]["audit_trail"]


def test_no_research_mutation_flag() -> None:
    result = _create(workflow_id="wf-immut", result_id="res-immut")
    assert result["provenance"]["research_mutated"] is False
    assert any("never modified" in lim.lower() for lim in result["limitations"])
