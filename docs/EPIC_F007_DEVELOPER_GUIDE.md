# EPIC-F007 — Developer Guide

## Entry

```tsx
import { ResearchWorkspace } from "@/components/research-workspace";
```

Route: `/research?ticker=AAPL&section=viewer`

## Preferences

```ts
import { useResearchWorkspacePrefsStore } from "@/lib/research-workspace";
```

## Keyboard

| Shortcut | Action |
|---|---|
| Ctrl/⌘ + Enter | Load research |
| 1–7 | Jump section |
| `[` / `]` | Toggle panels |

## Tests

```bash
cd apps/web && npm test -- src/lib/research-workspace/research-workspace.test.tsx
```

## Do not

- Add research list/archive/diff backend endpoints here
- Generate research or scores in the browser
- Fabricate library rows
