# EPIC-R002 — Developer Guide

## Generate in Python

```python
from dsp_platform.research_object import build_research_object, research_object_to_dict
from dsp_platform.institutional_report import (
    generate_institutional_report,
    institutional_report_to_dict,
)

ro = build_research_object(symbol="AAPL", data_bundle=bundle, analysis_payload=analysis)
report = generate_institutional_report(
    ro,
    report_id="rpt-fixed",
    generated_at="2026-07-28T12:00:00+00:00",
)
public = institutional_report_to_dict(report)

# Or via platform (dict in / dict out)
public = platform.generate_institutional_report(research_object_to_dict(ro))
```

## HTTP

```http
POST /api/v1/research/report
Content-Type: application/json

{
  "research_object": { "...": "Research Object v1.0.0 public dict" },
  "report_id": "optional-fixed-id",
  "generated_at": "optional-fixed-timestamp"
}
```

```http
GET /api/v1/research/report/schema
```

## Rules

1. Supply a complete Research Object — R002 never builds one from symbol alone.
2. Missing RO sections become unavailable report sections / fields.
3. Do not recompute valuation, MoS, or scores in the client.
4. Use fixed `report_id` / `generated_at` for deterministic tests.
