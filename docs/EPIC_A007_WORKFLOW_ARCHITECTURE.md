# EPIC-A007 — Workflow Architecture

```
Caller action (create / transition / comment / get)
        ↓
Workflow Templates (institutional_research_v1)
        ↓
Workflow Registry (process-local state only)
        ↓
Stages: draft → review → compliance_review → committee_review
        → approved → published   |   rejected (terminal)
        ↓
Approval Records · Reviewer Records · Comments · Decision History · Audit Trail
        ↓
Citations (artifact refs only) · Provenance · Audit metadata
```

Research artifacts are referenced by id — never loaded for mutation, never rewritten.
