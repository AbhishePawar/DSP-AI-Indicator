# EPIC-A007 — Developer Guide

## Package

`packages/dsp_platform/src/dsp_platform/institutional_workflow/`

| Module | Role |
|---|---|
| `models.py` | Stages / records / result |
| `templates.py` | Workflow templates |
| `registry.py` | In-memory workflow registry |
| `service.py` | Create / transition / comment / get |
| `citations.py` / `serde.py` / `validation.py` | Citations + gates |

Façade: `institutional_workflow_facade.py`  
Platform: `DSPPlatform.apply_institutional_workflow`  
API: `api_platform.api.routers.institutional_workflow`

## Tests

```bash
pytest packages/dsp_platform/tests/test_institutional_workflow.py -q
pytest packages/api_platform/tests/test_institutional_workflow_api.py -q
```

## Extending safely

- Add stages only with explicit `ALLOWED_TRANSITIONS` updates.
- Never write back into R001–R005 / A001–A006 payloads.
- Keep transitions deterministic and cited.
