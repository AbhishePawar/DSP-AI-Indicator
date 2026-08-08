# EPIC-R004 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/research/archive/schema` |
| POST | `/api/v1/research/archive/snapshots` |
| GET | `/api/v1/research/archive/snapshots/{snapshot_id}` |
| GET | `/api/v1/research/archive/lineages/{lineage_id}/history` |
| POST | `/api/v1/research/archive/compare` |
| POST | `/api/v1/research/archive/retention/evaluate` |

## Runtime

- Default store: process-local `InMemoryArchiveStore`
- No extra env vars required
- Suitable for RC / single-process; durable backends can implement `ArchiveStore`

## Retention

`RetainForeverPolicy` is default. `TimeToLivePolicy` is advisory — evaluation
never deletes snapshots. Wire durable purge separately if/when governance allows.

## Failure modes

| Condition | HTTP |
|---|---|
| Missing snapshot | 404 |
| Duplicate snapshot_id | 400 |
| Bad kind / empty payload | 400 |
| Missing parent | 404 |
