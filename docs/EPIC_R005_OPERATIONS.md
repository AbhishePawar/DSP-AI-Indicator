# EPIC-R005 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/research/diff/schema` |
| POST | `/api/v1/research/diff` |

## Runtime

- No additional env vars
- CPU-bound structural walk; cost scales with payload size
- Read-only against the Research Archive

## Failure modes

| Condition | HTTP |
|---|---|
| Missing snapshot | 404 |
| Kind mismatch | 400 |
| Invalid request body | 422 |

## Observability

Diff provenance includes left/right snapshot ids, kind, and engine version.
