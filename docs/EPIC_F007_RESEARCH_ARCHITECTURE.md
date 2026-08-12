# EPIC-F007 — Research Workspace Architecture

## Layout

Toolbar · Left nav (search, sections, recent/favourites/pinned) · Main sections · Right context

## Data sources

| Surface | Source |
|---|---|
| Library | `recentAnalyses`, local archive, recent report ids |
| Viewer | `loadResearchSession` / `loadArchivedSession` or `api.analyse` → `mapResearchView` |
| Archive browser | Local `listArchivedSessions` only |
| Diff | **Data unavailable.** (no diff API) |
| Institutional RS layout | Link to `/research/institutional` |
| Company detail page | Link to `/research/[ticker]` |

## Sections

Library · Viewer · Archive · Diff · AI · Compliance · Export

## Trust

Never invent research list rows, diffs, or scores. Missing server feeds stay
**Data unavailable.**
