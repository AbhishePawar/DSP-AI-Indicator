# EPIC-F009 — Developer Guide

## Entry

```tsx
import { SettingsWorkspace } from "@/components/settings-workspace";
```

Route: `/settings?section=appearance`

## Preferences

```ts
import { useSettingsPrefsStore } from "@/lib/settings";
```

Appearance is applied globally by `AppearanceApplicator` in the root layout.

## Keyboard

| Shortcut | Action |
|---|---|
| 1–8 | Jump section |
| `[` / `]` | Toggle panels |

## Tests

```bash
cd apps/web && npm test -- src/lib/settings/settings.test.tsx
```

## Do not

- Add preference sync backends
- Invent email / licence / logout-other-sessions behaviour
- Run business logic in preference handlers
