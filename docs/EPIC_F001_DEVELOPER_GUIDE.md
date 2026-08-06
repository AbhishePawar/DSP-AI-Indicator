# EPIC-F001 — Developer Guide

## Install

```bash
cd apps/web
npm install
npm test -- src/components/ds/ds.test.tsx
```

## Usage

```tsx
import { Button, EmptyState, PageLayout, ThemeSwitcher } from "@/components/ds";

export function Example() {
  return (
    <PageLayout title="Example" actions={<ThemeSwitcher />}>
      <Button>Continue</Button>
      <EmptyState />
    </PageLayout>
  );
}
```

## Paths

| Path | Role |
|---|---|
| `src/components/ds/**` | Design system |
| `components.json` | shadcn aliases |
| `src/lib/utils.ts` | `cn()` helper |
| `src/app/globals.css` | Token CSS variables |

## Storybook
Optional — deferred. Catalogue docs serve as the component index for F001.

## Do not
- Call APIs from `ds` components
- Change backend / routing / auth architecture here
- Build feature pages in F001
