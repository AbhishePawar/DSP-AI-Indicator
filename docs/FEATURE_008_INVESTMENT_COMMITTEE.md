# FEATURE-008 — AI Committee Consensus Engine (Phase 1)

| Field | Value |
|---|---|
| **Version** | `1.0.0` |
| **Status** | **Complete** — awaiting approval |
| **Last updated** | 2026-07-26 |
| **Package** | `investment_committee` **0.1.0** |
| **ADR** | [ADR-FEATURE-008-001](adr/ADR-FEATURE-008-001-investment-committee.md) |

## Executive Summary

Phase 1 delivers a deterministic multi-reviewer committee in
`packages/investment_committee` only. Five rule-based reviewers (Buffett, Value,
Quality, Growth, Risk) deliberate public IR + domain outputs into an explainable
consensus. Distinct from frozen G-era `ai_committee`. No LLM/ML. No
platform/API/UI wiring.

## Consensus methodology

Confidence-weighted rank mean + Risk Officer soft veto + agreement score.
Escalation flags for classic conflicts (e.g. great business / expensive).

## Architecture impact

New package registered; frozen `ai_committee` untouched; `/api/v1` unchanged.

## Test results

**15 PASS** package suite · integrity PASS · smoke/cycles PASS

## Feature health score

**91 / 100**

## Remaining technical debt

- TD-F015 platform composition of `investment_committee`
- TD-F016 tunable veto / additional reviewer roles
- Prior TD-F001…F014

## Recommended next feature

After approval: platform composition epic — **do not start without approval**.
