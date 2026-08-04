# EPIC-R005 — Developer Guide

```python
from dsp_platform.research_diff import diff_research_snapshots, research_diff_to_dict

result = diff_research_snapshots(
    "snap-a",
    "snap-b",
    diff_id="diff-fixed",
    created_at="2026-07-28T12:00:00+00:00",
)
public = research_diff_to_dict(result)
```

## HTTP

```http
POST /api/v1/research/diff
{
  "left_snapshot_id": "snap-a",
  "right_snapshot_id": "snap-b",
  "diff_id": "optional",
  "created_at": "optional"
}
```

```http
GET /api/v1/research/diff/schema
```

## Rules

1. Snapshots must be the same `kind`.
2. Diff is structural equality only — do not treat change_summary as advice.
3. Use fixed `diff_id` / `created_at` for deterministic tests.
