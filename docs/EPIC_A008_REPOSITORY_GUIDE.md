# EPIC-A008 — Repository Guide

## Entity kinds

| Kind | Purpose |
|---|---|
| `research_ref` | Reference ids to R001–R005 artifacts |
| `workflow_record` | A007 workflow metadata / history |
| `approval_history` | Approval decision records |
| `audit_record` | Audit trail entries |
| `citation` | Citation rows (path/section required) |
| `provenance` | Provenance blobs |
| `metadata` | Generic platform metadata |

## Rules

- Payload must not contain `research_object`, `institutional_report`, or `analysis_payload`
- Refs must be non-empty when present
- Updates increment `version` and preserve `created_at`
