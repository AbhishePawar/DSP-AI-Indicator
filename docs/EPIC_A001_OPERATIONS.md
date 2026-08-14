# EPIC-A001 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/research/copilot/schema` |
| POST | `/api/v1/research/copilot/ask` |

## Runtime

- No additional env vars
- No provider network calls
- Conversation history is process-local (turn metadata only)

## Failure modes

| Condition | Behavior |
|---|---|
| No research context | `unavailable: true`, answer `Data unavailable.` |
| Section missing | Cited with `available: false`, message `Data unavailable.` |
| Missing snapshot_id | HTTP 404 |

## Observability

Response `audit` + `provenance` record intent, citation count, and that
providers/engines were not called.
