# EPIC-A010 — Admin Architecture

## Purpose

Thin enterprise console for operational visibility. Consumes existing artifacts only.

```
Admin Console (read-only API)
        │
        ├─ AuthService (A009) — users / roles / permissions / sessions
        ├─ PersistenceService (A008) — audit / workflow / research_ref metadata
        ├─ HealthPanel — static readiness (no engines)
        ├─ Config / Version / FeatureFlag viewers
        └─ Metrics / Timeline / Search / Export
```

## Rules

- Never execute engines or call providers
- Never modify research, reports, or archives
- No valuation / scoring / recommendations / calculations
- Preserve provenance and timestamps
- Deterministic ordered outputs

## Sources

| Source | Use |
|---|---|
| A008 metadata / audit_record / workflow_record / research_ref | viewers + export |
| A009 AuthService | user/role/session management & viewers |
| Package versions / env DSP_* / FeatureFlagManager | panels |

## Non-goals

No new research. No breaking API changes to prior epics.
