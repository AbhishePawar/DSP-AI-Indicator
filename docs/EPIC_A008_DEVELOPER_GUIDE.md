# EPIC-A008 — Developer Guide

## Package

`packages/persistence/src/persistence/`

| Module | Role |
|---|---|
| `models.py` | Entity / snapshot models |
| `storage.py` | In-memory provider |
| `repositories.py` | Typed CRUD + immutable snapshots |
| `transactions.py` | Begin / commit / rollback |
| `service.py` | Orchestration helpers |
| `serde.py` / `validation.py` | Deterministic gates |

Façade: `dsp_platform.persistence_facade`  
Platform: `persistence_schema`, `persist_entity`, `persist_workflow_record`, …  
API: `api_platform.api.routers.persistence`

## Tests

```bash
pytest packages/persistence/tests/test_persistence.py -q
pytest packages/api_platform/tests/test_persistence_api.py -q
```

## Extending safely

- Never store research payload bodies
- Never change A007 state-machine semantics from this package
- Add providers behind `StorageProviderPort` only
