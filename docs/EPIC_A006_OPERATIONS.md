# EPIC-A006 — Operations

## Endpoints

| Method | Path |
|---|---|
| GET | `/api/v1/policy/schema` |
| GET | `/api/v1/policy/default` |
| POST | `/api/v1/policy/evaluate` |

## Runtime

- No additional env vars
- No provider network calls
- Default policy used when `policy` omitted
- Exceptions waived by `rule_id` via request `exceptions` or policy payload

## Failure modes

| Condition | Behavior |
|---|---|
| Missing `subject` | HTTP 400/422 |
| Invalid rule kind/severity | HTTP 400 |
| Missing optional artifact for a rule | Rule outcome `unavailable` / `"Data unavailable."` |
| Violations present | Summary status `non_compliant` |
