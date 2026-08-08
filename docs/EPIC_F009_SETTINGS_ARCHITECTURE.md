# EPIC-F009 — Settings Architecture

## Layout

Toolbar · Left nav · Main settings panel · Right context

## Preference sources

| Concern | Source |
|---|---|
| Theme | `ThemeProvider` (`dsp.theme.v2`) + optional Persistence sync |
| Density / font / motion / contrast / focus | `dsp.settings.prefs.v1` → `<html>` dataset |
| Dashboard widgets | F004 `dashboardPrefsStore` |
| Sidebar / favourites / recent | F003 `uiStore` |
| Landing page | Persistence `UserPreference` (browser-scoped) |
| Profile / sessions | A009 `/auth/rbac/me`, A010 `/admin/sessions` |

## Trust

No cloud preference sync claims. No invented email prefs or logout-all.
Licence and missing fields → **Data unavailable.**
