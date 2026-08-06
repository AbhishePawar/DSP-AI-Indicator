# EPIC-R004 — Architecture

```
POST /api/v1/research/archive/snapshots
        ↓
[api_platform] research.router
        ↓
[dsp_platform] archive_research_snapshot()
        ↓
ResearchArchiveService
   → hash payload (SHA-256)
   → freeze MappingProxyType
   → InMemoryArchiveStore.put_if_absent()  (no overwrite)
```

## Package

| Path | Role |
|---|---|
| `research_archive/models.py` | Snapshot / version / comparison / retention |
| `research_archive/hashing.py` | Canonical JSON + SHA-256 |
| `research_archive/store.py` | Immutable store protocol + in-memory |
| `research_archive/retention.py` | Retention policy hooks |
| `research_archive/service.py` | Archive / get / history / compare |
| `research_archive/validation.py` | Structural + integrity validator |
| `research_archive/serde.py` | Serialize / deserialize |
| `research_archive_facade.py` | Platform helper |

## Boundaries

- Archives existing outputs only
- Never calls engines or mutates R001–R003 modules
- Additive HTTP only
