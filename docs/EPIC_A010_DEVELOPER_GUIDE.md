# EPIC-A010 — Developer Guide

## Package

```python
from admin import get_admin_service

svc = get_admin_service()
svc.dashboard(generated_at="2026-07-28T15:00:00+00:00")
svc.list_audit_records(subject="INFY")
svc.export_audit()
svc.health_panel()
```

## Platform

```python
from dsp_platform import DSPPlatform

p = DSPPlatform()
p.admin_schema()
p.admin_dashboard()
p.admin_system_metrics()
```

## Tests

```bash
pytest packages/admin/tests packages/api_platform/tests/test_institutional_admin_api.py -q
```

## Constraints

Do not modify A001–A009 packages to “enrich” the console. Extend `packages/admin`
and additive `/admin/*` routes only.
