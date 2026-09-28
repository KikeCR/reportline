# Reportline frontend

Vite + React 19 + TypeScript (strict), TanStack Query, and `elkjs` for the
org chart's layered graph layout. See the repo root [README](../README.md)
for how to run the whole stack, and [CLAUDE.md](../CLAUDE.md) for the
architecture rules.

## Layout

```
src/
  api/            fetch client, Zod schemas validated at the API boundary,
                  generated OpenAPI types (schema.d.ts - never hand-edited)
  context/        OrgContext/OrgProvider - the current tenant (X-Org-Id)
  features/
    orgchart/     the graph canvas, filters, detail drawer
    admin/        HRIS sync + quarantine tables
  test/           setup, a shared render helper, Page Objects
```

## Commands

```bash
npm run dev          # Vite dev server on :5173, proxies /api/v1 to :5001
npm run build         # tsc -b + production build
npm run typecheck     # tsc -b only
npm run lint          # ESLint
npm run test          # Vitest
npm run test:coverage # Vitest with coverage (thresholds in vite.config.ts)
npm run types         # regenerate src/api/schema.d.ts from ../api/openapi.json
```

## Contract with the backend

`src/api/schema.d.ts` is generated from `api/openapi.json` via
`openapi-typescript` - never hand-edited. `src/api/schemas.ts` defines Zod
schemas for every response the app reads, each checked against the
generated type at compile time (`Expect<Equal<z.infer<typeof X>,
components['schemas']['X']>>`), so a drifted Zod schema fails `tsc`, not
just at runtime.
