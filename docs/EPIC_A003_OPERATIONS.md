# EPIC-A003 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/research/monitoring/schema` |
| POST | `/api/v1/research/monitoring/watchlist` |
| POST | `/api/v1/research/monitoring/portfolio` |
| POST | `/api/v1/research/monitoring/track` |
| POST | `/api/v1/research/monitoring/evaluate` |

## Runtime

- No additional env vars
- No provider network calls
- Registry is process-local (in-memory); track ids are references only
- Diffs require R004 snapshots already present in the archive store

## Failure modes

| Condition | Behavior |
|---|---|
| Missing snapshot id pair | Alert `unavailable` / `"Data unavailable."` |
| Snapshot not in archive | Alert `unavailable` / `"Data unavailable."` |
| Kind mismatch on R005 | Alert `unavailable` / `"Data unavailable."` |
| Incomplete PI pair | Alert `unavailable` / `"Data unavailable."` |
