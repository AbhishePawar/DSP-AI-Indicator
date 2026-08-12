# EPIC-A005 — Developer Guide

## Package

`packages/dsp_platform/src/dsp_platform/institutional_committee/`

| Module | Role |
|---|---|
| `models.py` | Context / review / report |
| `context.py` | Context distributor |
| `agents.py` | Independent reviews |
| `registry.py` | Agent registry |
| `consensus.py` | Consensus + minority + summary |
| `service.py` | Orchestrator |
| `citations.py` / `serde.py` / `validation.py` | Citations + gates |

Façade: `institutional_committee_facade.py`  
Platform: `DSPPlatform.run_institutional_committee`  
API: `api_platform.api.routers.institutional_committee`

## Tests

```bash
pytest packages/dsp_platform/tests/test_institutional_committee.py -q
pytest packages/api_platform/tests/test_institutional_committee_api.py -q
```

## Extending safely

- Register new agents only via `AGENT_SPECS` + `AGENT_IDS` together.
- Never call providers/engines or invent values.
- Every opinion must cite source sections.
