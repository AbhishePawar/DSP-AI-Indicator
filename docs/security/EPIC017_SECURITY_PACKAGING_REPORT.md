# EPIC-017 Security Packaging Review

Generated: `2026-08-03T09:05:01.613395+00:00`

**Result:** 13/13 checks passed

| Check | Status | Detail |
|---|---|---|
| .env.production gitignored | PASS | expected in .gitignore |
| .env.production.example allowed | PASS |  |
| no committed .env.production file | PASS | file absent or local-only |
| API runs as USER dsp | PASS |  |
| Web runs as USER dsp | PASS |  |
| API HEALTHCHECK present | PASS |  |
| Web HEALTHCHECK present | PASS |  |
| compose uses env substitution for DB password | PASS |  |
| security middleware present | PASS |  |
| security headers referenced | PASS | see docs/security/PRODUCTION_SECURITY_GUIDE.md |
| k8s API drops ALL caps | PASS |  |
| k8s runAsNonRoot | PASS |  |
| no hardcoded secrets in deploy/ | PASS |  |

## Scope

- Headers/cookies: see `docs/security/PRODUCTION_SECURITY_GUIDE.md` (EPIC-016)
- Container hardening: non-root USER, HEALTHCHECK, capability drop in k8s
- Secrets: ConfigMap vs Secret separation; ExternalSecrets recommended
- SBOM: `python scripts/ops/generate_sbom.py`
- Image scanning: `trivy image dsp-api:2.0.0` (CI optional)

## Fixes applied in EPIC-017

- Added k8s securityContext (runAsNonRoot, drop ALL)
- Documented secrets abstraction under `deploy/docker/secrets.md`
- SBOM generation script + lite inventories

## Residual risks

- Next.js CSP still allows `'unsafe-inline'` / `'unsafe-eval'` (tracked, not redesigned)
- In-cluster Postgres StatefulSet is reference-only; prefer managed + PITR
- Full CycloneDX requires syft/cyclonedx CLI in CI

```json
{
  "epic": "017",
  "passed": 13,
  "total": 13
}
```
