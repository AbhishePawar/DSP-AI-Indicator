# EPIC-A010 — Operations Guide

## API (additive, `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/admin/schema` | Capabilities / rules |
| GET | `/admin/dashboard` | Aggregate counts + health |
| GET/POST | `/admin/users` | List / create users |
| GET | `/admin/users/{id}` | User detail |
| PUT | `/admin/users/{id}/roles` | Assign roles |
| GET/POST | `/admin/roles` | List / upsert roles |
| GET | `/admin/permissions` | Permission catalogue |
| GET | `/admin/sessions` | Session viewer |
| GET | `/admin/audit` | Audit log (+ filters) |
| GET | `/admin/audit/export` | Export audit metadata |
| GET | `/admin/workflow-history` | Workflow metadata history |
| GET | `/admin/research-archive` | Research **refs** only |
| GET | `/admin/timeline` | Activity timeline |
| POST | `/admin/search` | Search scopes: audit/workflow/users/sessions |
| GET | `/admin/health` | Health panel |
| GET | `/admin/configuration` | DSP_* config keys (secrets redacted) |
| GET | `/admin/versions` | Package versions |
| GET | `/admin/feature-flags` | Feature flags |
| GET | `/admin/metrics` | System metadata counts |

## Ops notes

- Default APIs remain open; pair with A009 `/auth/rbac/protect` when enforcing access
- Export is metadata-only JSON; never includes research bodies
- Health panel does not invoke analysis pipelines
