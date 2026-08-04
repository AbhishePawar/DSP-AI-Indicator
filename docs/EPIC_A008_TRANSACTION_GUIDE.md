# EPIC-A008 — Transaction Guide

```python
from persistence import get_persistence_service

svc = get_persistence_service()
svc.begin()
try:
    svc.put(kind="metadata", entity_id="m1", payload={"ok": True})
    svc.commit()
except Exception:
    svc.rollback()
    raise
```

- Nested transactions are rejected
- Rollback restores the full storage checkpoint taken at `begin()`
- Deterministic: same checkpoint → same restored state
