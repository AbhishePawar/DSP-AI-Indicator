# EPIC-F008 — Developer Guide

## Entry

```tsx
import { AdminConsole } from "@/components/admin-console";
```

Route: `/admin?section=overview&user=&role=`

## API client

```ts
import { adminApi } from "@/lib/api/adminClient";
```

## Preferences

```ts
import { useAdminConsolePrefsStore } from "@/lib/admin-console";
```

## Keyboard

| Shortcut | Action |
|---|---|
| Ctrl/⌘ + Enter | Refresh admin queries |
| 1–8 | Jump section |
| `[` / `]` | Toggle panels |

## Access

Requires any of `manage_users` · `manage_roles` · `configure_platform` ·
`view_audit`, or role `administrator`.

## Tests

```bash
cd apps/web && npm test -- src/lib/admin-console/admin-console.test.tsx
```

## Do not

- Add new admin endpoints
- Compute metrics or invent rows in the browser
- Display research bodies from archive refs
