# EPIC-A004 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/decision/workspace/schema` |
| POST | `/api/v1/decision/workspace` |

## Runtime

- No additional env vars
- No provider network calls
- Caller must supply artifacts (workspace does not fetch or archive)

## Failure modes

| Condition | Behavior |
|---|---|
| Invalid `kind` | HTTP 400 / `"Data unavailable."` |
| Missing `subject` | HTTP 400 |
| Missing optional artifact | Panel `unavailable` / `"Data unavailable."` |
