# EPIC-A007 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/workflow/schema` |
| GET | `/api/v1/workflow/templates` |
| POST | `/api/v1/workflow/action` |

## Runtime

- No additional env vars
- No provider network calls
- Registry is process-local (in-memory)
- Artifact refs are ids only

## Failure modes

| Condition | Behavior |
|---|---|
| Unknown / missing workflow | HTTP 400 · `"Data unavailable."` |
| Invalid transition | HTTP 400 |
| Terminal stage transition | HTTP 400 |
| Empty comment body | HTTP 400 |
