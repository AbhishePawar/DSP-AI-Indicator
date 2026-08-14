# EPIC-F010 — Developer Guide

## Helpers

```ts
import {
  CRITICAL_ROUTES,
  RESPONSIVE_VIEWPORTS,
  useCollapsePanelsBelowLg,
} from "@/lib/a11y";
```

## Tests

```bash
cd apps/web && npm test -- src/lib/a11y/a11y-responsive.test.tsx
```

## Do not

- Add product features in the name of “polish”
- Change backend or API contracts
- Invent scoring or client calculations
