# llm_adapters

| Field | Value |
|---|---|
| **Package** | `llm_adapters` |
| **Version** | `0.1.0` |
| **Status** | Active — edge adapters |
| **Role** | External LLM provider adapters implementing LanguageModelPort outside frozen `copilot` |

## Public API

```python
from llm_adapters import (
    CopilotCompleteService,
    ProviderRegistry,
    build_default_registry,
    load_llm_config,
)
```

## Rules

- Adapters explain / complete grounded prompts — **never** override deterministic engine math.
- Depends on `copilot` ports + `httpx`; must not import valuation / recommendation / committee engines.
- Deterministic composer remains the safe fallback when providers are unavailable.

## Tests

```powershell
pytest packages/llm_adapters --import-mode=importlib
```
