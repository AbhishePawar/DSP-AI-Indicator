# EPIC-R002 — Architecture

## Flow

```
[Caller]
   POST /api/v1/research/report
        { research_object: <R001 dict> }
        ↓
[api_platform]  research.router  (validate request only)
        ↓
[dsp_platform]  DSPPlatform.generate_institutional_report()
        ↓
[dsp_platform.institutional_report]
   research_object_from_dict (if needed)
   InstitutionalReportGenerator
     ← Research Object ONLY
   validate_institutional_report()
   institutional_report_to_dict()
```

## Package layout

| Path | Role |
|---|---|
| `institutional_report/models.py` | Frozen report models |
| `institutional_report/mapper.py` | Read-only field extraction |
| `institutional_report/generator.py` | RO → report projection |
| `institutional_report/validation.py` | RS section presence validator |
| `institutional_report/serde.py` | Serialize / deserialize |
| `institutional_report_facade.py` | Platform helper |

## Boundaries

- Does **not** call D001–D005 or analysis engines
- Does **not** mutate Research Object
- Does **not** calculate MoS, scores, or valuations
- Additive HTTP only (`/research/report`, `/research/report/schema`)
