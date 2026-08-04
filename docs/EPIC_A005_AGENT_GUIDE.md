# EPIC-A005 — Agent Guide

## Agents (deterministic order)

| ID | Focus (artifact sections) |
|---|---|
| `buffett` | business_quality, margin_of_safety, identity |
| `graham` | margin_of_safety, valuation, financial_statements |
| `lynch` | identity, market_data, recommendation |
| `quality` | business_quality, explainability |
| `risk` | risk, scenarios, corporate_actions |
| `governance` | audit, explainability, institutional_report |
| `valuation` | valuation, margin_of_safety (availability only) |
| `devils_advocate` | diffs, monitoring alerts, portfolio gaps, core missing sections |

## Stances

| Stance | Meaning |
|---|---|
| `supportive` | Required focus evidence present |
| `cautionary` | Gaps, conflicts, or alerts cited from artifacts |
| `unavailable` | No usable evidence for the lens |

## Confidence

Categorical coverage only: `high` / `medium` / `low` / `unavailable`  
(not a numeric score).

## Consensus

Majority stance among usable (non-unavailable) reviews. Ties prefer `cautionary`.
Committee confidence = minimum confidence among usable agents.
