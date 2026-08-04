# EPIC-R005 — Architecture

```
POST /api/v1/research/diff
   { left_snapshot_id, right_snapshot_id }
        ↓
[api_platform] research.router
        ↓
[dsp_platform] diff_research_snapshots()
        ↓
load R004 snapshots (read-only)
        ↓
ResearchDiffEngine
   → schema / version / archive metadata compare
   → section walk (R001/R002/R003 section maps)
   → structural equality field diffs
   → change_summary counts
```

## Package

| Path | Role |
|---|---|
| `research_diff/loader.py` | Read-only snapshot loader |
| `research_diff/walker.py` | Deterministic structural walk |
| `research_diff/engine.py` | Diff engine |
| `research_diff/models.py` | Diff result models |
| `research_diff/validation.py` | Validator |
| `research_diff/serde.py` | Serialize / deserialize |
| `research_diff_facade.py` | Platform helper |

## Boundaries

- Never mutates R004 store or snapshot payloads
- Never calls valuation/scoring engines
- Additive HTTP only
