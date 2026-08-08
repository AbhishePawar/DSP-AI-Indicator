# ARCH-001 — Buffett Indicator Report (Non-Architectural)

Status: **COMPLETE** · Frontend **v1.1.0** · Backend **unchanged** (`dsp_platform@1.0.0`)

## Summary

Adds a **Buffett Indicator Analysis** section to Company Analysis and Research
workspaces as a **reporting synthesis** of existing `/api/v1/analyse` outputs.

- No new package
- No pipeline stage
- No engine / recommendation / valuation changes
- No API redesign
- No duplicate fundamental calculations (ROE, DCF, MoS, moat, etc.)

## Position in report

Executive Summary → Financial → Valuation → Quality → AI Committee → Final Recommendation → **Buffett Indicator Analysis**

## Honesty rules

- Every statement cites existing stage / summary fields
- Missing fields (e.g. ROE when not on AnalyseResponse) → **Unavailable**
- Letter grades are display bands of **existing** stage scores only
- Buffett Action maps existing recommendation/committee decisions → BUY / WATCH / HOLD / AVOID

## Docs

- This README
- Frontend: `apps/web/src/lib/buffett-indicator/`
- UI: `BuffettIndicatorSection`
