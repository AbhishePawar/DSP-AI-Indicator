# EPIC-F008 — Administration Console Architecture

## Layout

Toolbar · Left nav (sections + selection) · Main sections · Right context

## Data sources (A010)

| Surface | Endpoint |
|---|---|
| Overview | `GET /admin/dashboard` |
| Identity | `/admin/users`, `/roles`, `/permissions`, `/sessions` |
| Audit | `/admin/audit`, `/timeline`, `/search`, `/audit/export` |
| Platform | `/admin/health`, `/configuration`, `/versions`, `/feature-flags` |
| Metrics | `GET /admin/metrics` |
| Workflow | `GET /admin/workflow-history` |
| Research | `GET /admin/research-archive` (refs only) |

## Trust

Never invent users, audit rows, metrics, or research bodies. Missing or empty
feeds stay **Data unavailable.** Secrets from configuration remain unavailable.
