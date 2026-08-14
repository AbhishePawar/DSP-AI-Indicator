# EPIC-R001 — Developer Guide

## Build in Python

```python
from dsp_platform import DSPPlatform, PlatformBuilder, PlatformConfiguration
from dsp_platform.research_object import (
    build_research_object,
    research_object_to_dict,
)

# Low-level (no network)
obj = build_research_object(
    symbol="AAPL",
    data_bundle=existing_d005_bundle,       # optional
    analysis_payload=existing_analyse_payload,  # optional
    valuation_signals=request_signals,     # optional
    object_id="ro-fixed-id",               # for determinism
    created_at="2026-07-28T12:00:00+00:00",
)
public = research_object_to_dict(obj)

# Platform façade (may fetch D005)
platform = (
    PlatformBuilder()
    .with_configuration(PlatformConfiguration(require_analysis_service=False))
    .build()
)
public = platform.build_research_object(
    "AAPL",
    analysis_payload=existing_analyse_payload,
    fetch_data_bundle=True,
)
```

## HTTP

```http
POST /api/v1/research/object
Content-Type: application/json

{
  "symbol": "AAPL",
  "fetch_data_bundle": true,
  "analysis_payload": { "...": "AnalyseResponse.payload" },
  "valuation_signals": null
}
```

```http
GET /api/v1/research/object/schema
```

## Rules of use

1. Pass **already produced** analysis / valuation outputs — do not expect R001 to score.
2. Treat every section as read-only; never mutate returned dicts in place expecting persistence.
3. Missing data → `"Data unavailable."` — do not fabricate client-side.
4. Prefer fixed `object_id` / `created_at` when asserting determinism in tests.

## Deserialization

```python
from dsp_platform.research_object import research_object_from_dict

obj = research_object_from_dict(public_dict)  # re-validates + re-freezes
```
