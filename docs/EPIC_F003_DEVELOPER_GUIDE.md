# EPIC-F003 — Developer Guide

## Imports

```ts
import { AppLayout, PageContainer, LoadingLayout } from "@/components/layout";
import {
  SHELL_NAV,
  filterShellNav,
  breadcrumbsForPath,
  useUiStore,
} from "@/lib/shell";
```

## Adding a shell nav item

1. Add to `SHELL_NAV` in `navigationRegistry.ts` (with `access` if needed).
2. Ensure the route exists or is frozen for a later epic — **do not** implement
   feature pages in shell epics.
3. Optional: add to `AUX_ROUTES` for command-palette-only destinations.

## Command palette

`ShellCommandPalette` mounts inside `AppLayout`. Shortcut: **Ctrl+K** / **⌘K**.
Items: Favourites, Recent, Navigation, Actions (toggle favourite).

## Responsive

| Breakpoint | Behaviour |
|---|---|
| `< md` | Sidebar drawer via Menu button |
| `≥ md` | Persistent sidebar; collapse toggle |

## Accessibility

- Skip to content (root)
- Sidebar landmark + arrow / Home / End keyboard nav
- Breadcrumb `nav`
- Command dialog labelled
- Focus rings via F001 tokens
- `motion-reduce` on width / scroll transitions

## Tests

```bash
cd apps/web && npm test -- src/lib/shell/shell.test.tsx
```

## Do not

- Change backend / `/api/v1` contracts
- Put business logic in the shell
- Bypass F001 for new chrome controls
