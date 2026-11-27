# Gitleaks false-positive register

**Tracking:** Master remediation checklist, [issue #36](https://github.com/AbhishePawar/DSP-AI-Indicator/issues/36).

**Purpose:** Document the exact historical Gitleaks findings suppressed by the repository-root `.gitleaksignore`.

**Evidence source:** GitHub Actions Secret scan and Secret scan (Gitleaks), PR #34 head `e664bf992b88f2fabbee333c640671e3b4980b8f`, run 40942609211, 29 October 2026.

## Review result

The scan traversed 1,146 commits and reported 23 `generic-api-key` findings. The reported locations were inspected at their finding commits. They are synthetic test values, WebAuthn challenge/public-key test data, placeholder environment-variable declarations, generated-secret variable flow, sample JWT/test configuration, ordinary identifiers/storage keys, or documentation prose—not live provider credentials.

The ignore file contains the exact Gitleaks fingerprints only. It does **not** exclude whole files, directories, rules, or future commits. If a line changes, a new fingerprint is generated and the scanner should report it again.

| Finding group | Reviewed interpretation |
|---|---|
| `test_recovery_api_scenarios.py` | Synthetic in-memory adapter key used by a negative-path test |
| Passkey/WebAuthn test files | Test challenge and public-key fixture values; not private credentials |
| `deploy/docker/staging.env.example` | Empty secret-variable placeholders; no value is assigned |
| Share-count acquisition test | NSE instrument identifier/test fixture, not a credential |
| `dsp_platform/share_counts.py` | Explicit `p109-fixture-key` used only by the P109 fixture path |
| `auth/mfa_totp.py` | Runtime-generated TOTP secret variable; no hard-coded secret literal |
| P109/P110 journey and authenticity tests | Explicit `p109-fixture-key` / `p110-fixture-key` synthetic adapter keys |
| Supabase configuration test | Deliberately dummy JWT-shaped anon-key test string; not a live key |
| Phase 2B auth test | Explicit test-only JWT secret string |
| Enterprise auth documentation | Generic security-summary prose; no credential value |
| Identity reset test | Passwords generated within the test scenario |
| Recent analyses UI | Static browser storage key, not an authentication secret |

## Security policy

- Never add broad path, directory, or rule-level exclusions to silence a scan.
- Never ignore a finding merely because it appears in a test or documentation file; inspect the exact value and commit context first.
- If a finding is a real credential, revoke/rotate it and follow the incident process. Removing it from the latest tree alone does not invalidate a historical credential.
- Keep all new findings blocking until reviewed.
- Re-run both secret-scan workflows against the exact release candidate after this register is added.

## Scope limitation

This register documents the 23 historical findings observed in the cited PR #34 scan only. It is not a claim that every historical commit or every future scan is clean.
