# EPIC-R004 — Developer Guide

```python
from dsp_platform.research_archive import (
    ResearchArchiveService,
    InMemoryArchiveStore,
    archive_snapshot_to_dict,
)

service = ResearchArchiveService(InMemoryArchiveStore())
snap = service.archive(
    "research_object",
    research_object_dict,
    snapshot_id="snap-1",
    lineage_id="line-aapl",
    archived_at="2026-07-28T12:00:00+00:00",
)
v2 = service.archive(
    "research_object",
    research_object_dict_v2,
    parent_snapshot_id=snap.snapshot_id,
    archived_at="2026-07-28T13:00:00+00:00",
)
history = service.history("line-aapl")
comparison = service.compare(snap.snapshot_id, v2.snapshot_id)
```

## Platform

```python
platform.archive_research_snapshot("institutional_report", report_dict)
platform.get_research_snapshot(snapshot_id)
platform.list_research_version_history(lineage_id)
platform.compare_research_snapshots(a, b)
platform.evaluate_research_retention(snapshot_id)
```

## Rules

1. Never mutate returned payloads expecting archive updates.
2. Always archive complete R001/R002/R003 public dicts.
3. Use fixed ids/timestamps for deterministic tests.
