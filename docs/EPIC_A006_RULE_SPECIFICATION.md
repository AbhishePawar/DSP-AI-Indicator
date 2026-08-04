# EPIC-A006 — Rule Specification

## Rule kinds

| Kind | Params | Pass when |
|---|---|---|
| `require_source_present` | `source` | Artifact present |
| `require_section_available` | `section` | RO section `available` |
| `require_report_present` | — | R002 present |
| `require_committee_stance` | `stances[]` | Consensus stance ∈ list |
| `forbid_committee_stance` | `stances[]` | Consensus stance ∉ list |
| `forbid_missing_research` | — | A002 `missing_research` empty |
| `forbid_alert_severity` | `severities[]` | No matching A003 alerts |
| `require_diff_identical` | — | All diffs `identical_content` |

## Outcomes

`pass` · `warning` · `violation` · `unavailable` · `waived`

Rule `severity` (`violation`|`warning`) maps failing outcomes. Exceptions waive by `rule_id`.

## Default policy highlights

- Research Object required
- `margin_of_safety` available (violation)
- `business_quality` / `risk` available (warning)
- Committee consensus not `unavailable`
- No portfolio missing-research links
- No important/unavailable monitoring alerts
- Diffs identical when supplied
