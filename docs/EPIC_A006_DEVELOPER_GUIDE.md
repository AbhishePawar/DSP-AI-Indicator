# EPIC-A006 — Developer Guide

## Package

`packages/dsp_platform/src/dsp_platform/investment_policy/`

| Module | Role |
|---|---|
| `models.py` | Policy / rule / result |
| `loader.py` | Policy loader + default |
| `registry.py` | Rule + exception registries |
| `evaluator.py` | Deterministic rule evaluation |
| `service.py` | Compliance checker |
| `citations.py` / `serde.py` / `validation.py` | Citations + gates |

Façade: `investment_policy_facade.py`  
Platform: `DSPPlatform.evaluate_investment_policy`  
API: `api_platform.api.routers.investment_policy`

## Tests

```bash
pytest packages/dsp_platform/tests/test_investment_policy.py -q
pytest packages/api_platform/tests/test_investment_policy_api.py -q
```

## Extending safely

- Add rule kinds only with structural checks (no math).
- Every rule result must include citations.
- Keep rule order deterministic (`rule_id` sort).
