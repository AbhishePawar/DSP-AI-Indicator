# EPIC-A002 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/portfolio/intelligence/schema` |
| POST | `/api/v1/portfolio/intelligence` |

## Runtime

- No additional env vars
- No provider network calls
- Research must be supplied (or R004 `snapshot_ids`)

## Failure modes

| Condition | HTTP |
|---|---|
| Neither portfolio nor watchlist | 400 |
| Missing snapshot id | holding remains unlinked / Data unavailable. |
