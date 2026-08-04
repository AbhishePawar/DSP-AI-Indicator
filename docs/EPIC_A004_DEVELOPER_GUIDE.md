# EPIC-A004 — Developer Guide

## Package

`packages/dsp_platform/src/dsp_platform/decision_workspace/`

| Module | Role |
|---|---|
| `models.py` | Workspace / panel / timeline |
| `panels.py` | Panel builders |
| `timeline.py` | Timestamp aggregation |
| `citations.py` | Citation builder |
| `service.py` | Aggregation orchestration |
| `serde.py` / `validation.py` | Round-trip + gates |

Façade: `decision_workspace_facade.py`  
Platform: `DSPPlatform.build_decision_workspace`  
API: `api_platform.api.routers.decision_workspace`

## Tests

```bash
pytest packages/dsp_platform/tests/test_decision_workspace.py -q
pytest packages/api_platform/tests/test_decision_workspace_api.py -q
```

## Extending safely

- Add panels only by extending `PANEL_NAMES` and builders together.
- Never call providers/engines or invent values.
- Keep every panel cited.
