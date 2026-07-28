# security_platform

## Purpose

DSP Authentication & Security — JWT / RBAC / API keys / **PEP-001 identity**.

## Version

**0.2.0** · K1.2 + PEP-001

## Highlights

- Frozen RBAC roles/permissions
- Password auth (Argon2 preferred, scrypt reference)
- Refresh tokens + session tracking
- `SecurityBundle.create()` offline; `create_with_infrastructure(infra, consent_store=…)` for PEP-002 ports
- India ports: consent (composable), PAN/DigiLocker/Aadhaar/KYC (stubs)

## Docs

- [PEP_001_ENTERPRISE_IDENTITY_SECURITY.md](../../docs/PEP_001_ENTERPRISE_IDENTITY_SECURITY.md)
- [IDENTITY_ARCHITECTURE.md](../../docs/IDENTITY_ARCHITECTURE.md)
- [RBAC_MODEL.md](../../docs/RBAC_MODEL.md)
- [SECURITY_GUIDE.md](../../docs/SECURITY_GUIDE.md)
- [AUTHENTICATION_FLOW.md](../../docs/AUTHENTICATION_FLOW.md)

## Tests

```bash
pytest packages/security_platform/tests -q --import-mode=importlib -p no:cov
```

## Optional

```bash
pip install "security-platform[argon2]"
```
