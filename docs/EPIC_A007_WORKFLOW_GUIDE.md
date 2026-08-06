# EPIC-A007 — Workflow Guide

## Stages

| Stage | Next |
|---|---|
| `draft` | `review` |
| `review` | `compliance_review`, `rejected` |
| `compliance_review` | `committee_review`, `rejected` |
| `committee_review` | `approved`, `rejected` |
| `approved` | `published` |
| `rejected` | — |
| `published` | — |

## Create

```http
POST /api/v1/workflow/action
{
  "action": "create",
  "subject": "AAPL",
  "artifact_refs": {
    "research_object_id": "ro-1",
    "report_id": "rpt-1",
    "committee_report_id": "ic-1",
    "compliance_result_id": "pol-1"
  }
}
```

## Transition

```http
POST /api/v1/workflow/action
{
  "action": "transition",
  "workflow_id": "wf-1",
  "to_stage": "review",
  "actor_id": "analyst-1"
}
```

## Assign reviewer / history / approve / reject

Actions: `assign_reviewer`, `history`, `approve`, `reject`, `comment`, `get`.
