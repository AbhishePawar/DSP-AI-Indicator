# EPIC-A003 — Developer Guide

## Package

`packages/dsp_platform/src/dsp_platform/research_monitoring/`

| Module | Role |
|---|---|
| `models.py` | Alert / track / evaluate result |
| `registry.py` | Watchlist + portfolio registry + snapshot tracks |
| `alerts.py` | Diff → alert + portfolio delta alerts |
| `service.py` | Evaluate orchestration |
| `serde.py` / `validation.py` | Round-trip + gates |

Façade: `research_monitoring_facade.py`  
Platform: `DSPPlatform.evaluate_research_monitoring` (+ register/track helpers)  
API: `api_platform.api.routers.research_monitoring`

## Tests

```bash
pytest packages/dsp_platform/tests/test_research_monitoring.py -q
pytest packages/api_platform/tests/test_research_monitoring_api.py -q
```

## Extending safely

- Prefer new alert types over mutating existing severities.
- Never call data providers or analysis engines from this package.
- Keep citations mandatory for every alert.
