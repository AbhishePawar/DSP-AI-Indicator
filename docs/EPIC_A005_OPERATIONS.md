# EPIC-A005 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/committee/schema` |
| GET | `/api/v1/committee/agents` |
| POST | `/api/v1/committee/run` |

## Runtime

- No additional env vars
- No provider network calls
- Caller supplies artifacts; committee does not fetch or mutate them

## Failure modes

| Condition | Behavior |
|---|---|
| Missing `subject` | HTTP 400/422 |
| No artifacts supplied | Consensus `unavailable` / agent findings `"Data unavailable."` |
| Partial sections | Agents return `cautionary` or `unavailable` with citations |
