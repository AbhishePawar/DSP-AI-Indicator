# EPIC-A008 — Persistence Architecture

```
Platform façade
        │
        ▼
PersistenceService
        │
        ├─ RepositoryRegistry
        ├─ TransactionManager (begin / commit / rollback)
        ├─ Deterministic serde + content hash
        └─ StorageProviderPort
              └─ InMemoryStorageProvider (default)
                 (future: Postgres / SQLite / DuckDB / object storage)

Repositories (references & metadata only)
  research_ref · workflow_record · approval_history
  audit_record · citation · provenance · metadata
  + immutable snapshots (workflow | audit | metadata)
```

Research content is never duplicated. Workflow state machine (A007) is unchanged.
