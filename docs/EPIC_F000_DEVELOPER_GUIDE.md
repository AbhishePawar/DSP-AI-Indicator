# EPIC-F000 — Developer Guide

## Run

```bash
cd apps/web
npm install
npm run test
npm run lint
npm run format:check
npm run dev
```

## Foundation imports

```ts
import {
  FRONTEND_FOUNDATION_VERSION,
  FROZEN_FEATURE_ROUTES,
  colorTokens,
  apiStrategy,
} from "@/foundation";
```

## Rules for F001+

1. Implement design system primitives (shadcn) mapped to PR1.2 tokens
2. Do not rebuild frozen feature pages until their epic
3. Do not modify backend packages or API contracts
4. Prefer extending `foundation/` contracts over inventing parallel architecture
5. Storybook optional — add only if F001 needs visual regression for primitives

## Testing

Vitest covers foundation freeze contracts: `src/foundation/foundation.test.ts`
