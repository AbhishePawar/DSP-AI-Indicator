# EPIC-F000 — Folder Structure

```
apps/web/
├── eslint.config.mjs          # F000 ESLint baseline
├── .prettierrc.json           # F000 Prettier
├── package.json               # foundationVersion 0.1.0 + approved stack
├── tsconfig.json              # @/* alias
├── vitest.config.ts
└── src/
    ├── app/                   # App Router (existing pages — DO NOT rebuild in F000)
    ├── components/
    │   ├── layout/            # Existing AppLayout / chrome
    │   └── ui/                # Interim primitives → migrate to shadcn in F001
    ├── foundation/            # ★ F000 architecture freeze (new)
    │   ├── version.ts
    │   ├── technology.ts
    │   ├── tokens/
    │   ├── routes/
    │   ├── layout/
    │   ├── state/
    │   ├── api/
    │   ├── auth/
    │   ├── ux/
    │   ├── components/
    │   └── index.ts
    ├── lib/
    │   ├── api/               # Existing /api/v1 client
    │   ├── auth/              # Existing JWT session
    │   └── env.ts             # + foundationVersion
    ├── providers/
    └── hooks/
```

## Import alias

`@/*` → `./src/*` (already configured)
