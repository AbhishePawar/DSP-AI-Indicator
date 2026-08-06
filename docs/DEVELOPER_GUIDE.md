# EPIC-A009 — Developer Guide

## Install / path

Root `pyproject.toml` includes `packages/auth/src` on `pythonpath`.
`dsp_platform` depends on `auth`.

## Quick start

```python
from auth import get_auth_service, reset_auth_service_for_tests, AuthService
from persistence import get_persistence_service

svc = get_auth_service()
svc.create_user(
    username="analyst1",
    email="a@example.com",
    password="Secret123!",
    roles=["research_analyst"],
    password_salt="aabbccddeeff0011",  # tests only — omit in prod
)
login = svc.login(username="analyst1", password="Secret123!")
token = login["tokens"]["access_token"]
svc.protect(token, "read_research")
```

## Platform façade

```python
from dsp_platform import DSPPlatform

p = DSPPlatform()
p.create_auth_user(...)
p.auth_login(...)
p.auth_current_user(token)
p.protect_with_permission(token, "view_audit")
```

## Tests

```bash
pytest packages/auth/tests packages/api_platform/tests/test_institutional_auth_api.py -q
```

## Constraints

Do not modify `packages/persistence`, research/valuation/workflow packages, or
legacy `/auth/login` behaviour when extending RBAC.
