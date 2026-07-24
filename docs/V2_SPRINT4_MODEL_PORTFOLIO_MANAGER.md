# Epic V2.0 Sprint 4 — Model Portfolio Manager

**Web:** `2.0.0`

## Mission

Build, review, compare, and present model portfolios using demo DSP research summaries. No trading, broker sync, or persistence.

## Surfaces

- `/advisor/portfolios` — Library (Growth → Custom)
- `/advisor/portfolios/builder` — Session builder (add/remove/reorder/% + 100% warning)
- `/advisor/portfolios/compare` — Model A vs B
- `/advisor/portfolios/templates` — Aggressive Growth → Custom
- `/advisor/portfolios/notes` — Aggregated demo notes

## Trust

Reuses demo research envelopes for holdings. Does not alter Evidence · Confidence · Methodology · Limitations · Investment Thesis. Does not call Portfolio Engine.

## Enable

`NEXT_PUBLIC_ADVISOR_DEMO=true`
