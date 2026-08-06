# EPIC-F006 — Portfolio Architecture

## Layout

Same institutional chrome pattern as F005:

Toolbar · Left nav (selector, sections, watchlist) · Main sections · Right context

## Data sources (honest)

| Surface | Source |
|---|---|
| Holdings list | `PortfolioProvider` session / persistence |
| Activities | Session activity log |
| Watchlist / favourites / notes | Local Zustand prefs |
| Research report links | Local recent report ids |
| Portfolio value / weights / risk / P&L | **Data unavailable.** (no API) |
| Committee / monitoring / workflow feeds | **Data unavailable.** (no API) |

## Sections

Summary · Holdings · Research · AI · Monitoring · Compliance · Export

## Trust

Do not reuse `portfolioWorkspace.finalizePortfolio`, equal-weight rebalance
as product analytics, or hardcoded portfolio values.
