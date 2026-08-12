# EPIC-R001 — Architecture

## Flow

```
[Caller / thin client]
   POST /api/v1/research/object
        ↓
[api_platform]  research.router  (validate request only)
        ↓
[dsp_platform]  DSPPlatform.build_research_object()
        ↓
 optional D005  get_unified_data_bundle(symbol)
        ↓
[dsp_platform.research_object]
   ResearchObjectBuilder
     ← data_bundle (D005)
     ← analysis_payload (existing /analyse public dict)
     ← valuation_signals (existing request signals)
        ↓
   validate_research_object()
        ↓
   research_object_to_dict()  → immutable public JSON
```

## Package layout

| Path | Role |
|---|---|
| `dsp_platform/research_object/models.py` | Frozen models + freeze helpers |
| `dsp_platform/research_object/builder.py` | Aggregate-only builder |
| `dsp_platform/research_object/validation.py` | Structural validator |
| `dsp_platform/research_object/serde.py` | Serialize / deserialize |
| `dsp_platform/research_object_facade.py` | Platform helper |
| `api_platform/api/routers/research.py` | Additive HTTP surface |

## Boundaries

- Does **not** import valuation/scoring engines for computation
- Does **not** modify D001–D005 adapters or `/analyse`
- Analysis must be supplied by caller — builder never re-runs the pipeline
- Partial D005 failures remain per-section unavailable (CV-001)

## Additive HTTP

- `GET /api/v1/research/object/schema`
- `POST /api/v1/research/object`
