# Release Checklist — 2.0.0 / 2.0.0

- [ ] `python scripts/release/validate_release.py` PASS
- [ ] `python scripts/ops/certify_p7_2.py` PASS
- [ ] `python scripts/ops/certify_p7.py` PASS (infra)
- [ ] CI workflows green on release branch
- [ ] Frontend `npm test` green
- [ ] Backend architecture + smoke green
- [ ] Docker images tagged `dsp-api:2.0.0` / `dsp-web:2.0.0`
- [ ] `PRODUCTION_VERSION_MANIFEST.json` matches tags
- [ ] Changelog section present for `2.0.0`
- [ ] No secrets in commit (`.env.production` absent)
- [ ] Deploy dry-run documented
- [ ] Backup + rollback scripts present
- [ ] Legal / Research Mode disclaimer still linked
- [ ] SBOM + checksums attached under `release/`

**API contract:** `v1.0.0` (behaviour frozen)
