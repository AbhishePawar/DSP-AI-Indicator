# EPIC-A001 — Copilot Guide

```python
from dsp_platform.research_copilot import ask_research_copilot

response = ask_research_copilot(
    "What is the margin of safety?",
    research_object=ro_dict,
    report=report_dict,          # optional
    snapshot_id="snap-1",        # optional R004
    research_diff=diff_dict,     # optional R005
    response_id="resp-fixed",
    created_at="2026-07-28T12:00:00+00:00",
)
```

## HTTP

```http
POST /api/v1/research/copilot/ask
{
  "question": "What is the current price?",
  "research_object": { "...": "R001" },
  "report": { "...": "R002" },
  "snapshot_id": "optional-r004-id",
  "research_diff": { "...": "R005" }
}
```

```http
GET /api/v1/research/copilot/schema
```

## Guarantees

Every answer includes citations to section paths when context exists.
No external LLM is required; mode is extractive grounded.
