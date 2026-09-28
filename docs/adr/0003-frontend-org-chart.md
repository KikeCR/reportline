# 0003 - The React org chart viewer

## Status

Accepted

## Context

Phase 3 builds the first real UI: a graph visualization (elkjs layered
layout) plus the surrounding app shell (filters, a detail drawer). The
brief's own ADR list (0001 org-as-dag, 0002 api-contract, 0003
tenant-scoping, 0004 sync-conflict-rules, 0005 llm-safety) didn't reserve a
slot for frontend decisions; this ADR takes the next open number rather than
renumbering anything already written - later phases' ADRs simply land at
0004+ instead of the brief's original numbering.

Before writing any component, this phase loaded the `dataviz` skill for the
graph's design system - an org chart is a node-link diagram, and the
brief's own explicit ask was that this not be a generic scaffold.

## Decision

### Department color is a text-first accent, never a color block

The dataviz skill's categorical palette (8 validated hues) covers the 6
departments (5 real + Executive) cleanly on adjacent-pair CVD safety, but
three of those hues (magenta, yellow, aqua) fall below 3:1 contrast on the
light surface - the skill's own documented "relief rule" for that case is
to ship visible direct labels, never rely on the hue alone. Rather than
paint node cards with a department-colored fill (the "thick saturated
block" anti-pattern the skill explicitly calls out), department color is a
4px left-border accent plus the department name as always-visible text.
Identity comes from the label; color is a reinforcing cue, not the sole
channel - satisfying the relief rule by construction rather than needing a
fallback table view. The palette was run through the skill's own
`validate_palette.js` in both light and dark mode before use (all checks
pass; the light-mode contrast WARN is exactly the case the text label
mitigates).

### Vacant is a muted/dashed state, not a status color

The dataviz skill's status palette (good/warning/serious/critical) is for
severity, and "vacant" isn't a severity - it's neutral. Using a status hue
would misapply a channel reserved for "something is wrong" to a routine
organizational fact. Vacant positions instead get a dashed border, a muted
surface, and an explicit "Vacant" text badge - the same
icon-plus-label-never-color-alone principle the skill applies to status
colors, adapted to a binary occupancy fact instead of a four-level
severity scale.

### Edge styling follows the skeleton/overlay distinction directly

Primary solid edges (the `$graphLookup` skeleton - see ADR 0001) render as
2px solid lines in the primary ink color; non-primary solid edges (co-manager
overlays) and dotted-line edges render at reduced visual weight (muted
color; dotted edges additionally get an actual dashed stroke, since here
the visual metaphor and the domain concept happen to coincide). This
matches the skill's "2px lines, round caps" mark spec and its rule that an
overlay never outweighs the primary encoding.

### elkjs: `elk.bundled.js`, not the package's default entry

`elk.layout()`'s browser usage was verified against elkjs's own installed
`.d.ts` before writing `useGraphLayout.ts`. The default `elkjs` entry
(`lib/main.js`) is Node-oriented: it conditionally `require('web-worker')`
only if a `workerUrl` option is passed (which this app never does, so at
runtime it silently falls back to an in-process "fake worker" and works
fine in dev). Vite's **production** build, however, statically resolves
every `require()` call regardless of whether the branch executes, and fails
because `web-worker` isn't installed (it's an optional peer for Node worker
threads, not needed here). `npm run dev` never surfaced this - it only
showed up running `npm run build`, which is why that command was run before
calling the phase done. The fix is `elkjs/lib/elk.bundled.js`, the same
default export, pre-bundled without the Node worker-thread branch at all -
not a workaround so much as using the entry point elkjs ships for exactly
this bundler scenario.

### Collapse/expand: a hidden-id set, not a re-fetch

Collapsing a node hides its skeleton descendants client-side
(`computeHiddenIds` in `graphMapping.ts`) rather than asking the backend for
a filtered graph - the full graph for a tenant is small (~120 nodes at seed
scale) and already fetched once; recomputing visibility and re-running elk
locally is both simpler and faster than a round trip per toggle. A
collapsed node stays visible; only its descendants hide, so the user never
loses their place.

### Keyboard navigation: arrow keys move spatially, Tab still works

Every node is a real `<button>`, so Tab-order navigation works for free.
Arrow keys additionally move focus to the nearest node in the pressed
direction (`findNodeInDirection` in `OrgChart.tsx`), using the coordinates
elk already computed - a org chart's natural navigation is spatial (up to
your manager, down to a report), which raw DOM tab order doesn't capture
since it follows array order, not the rendered layout.

### The interim tenant field mirrors the backend's interim header exactly

`OrgContext`/`OrgProvider`/`useOrg` hold a plain `orgId` string, entered via
a text field in the app header and persisted to `localStorage`. This is the
frontend half of ADR 0002's `X-Org-Id` placeholder - deliberately just as
provisional, and replaced in Phase 4 by real login, at which point `useOrg`
(or its Phase 4 equivalent) starts returning the org id decoded from a JWT
instead of user-typed text. Every data-fetching hook already goes through
`useOrg`, so that swap is contained to this one context.

### Zod-vs-generated-types drift check is a compile-time equality, not a runtime test

Documented in ADR 0002 already; noted here because it's implemented in this
phase's `api/schemas.ts`. Each Zod schema is followed by a
`type _CheckX = Expect<Equal<z.infer<typeof XSchema>, components['schemas']['X']>>`
assertion - `npm run typecheck` fails if a schema and its generated type
diverge. This is more precise than a runtime assertion would be, since
structural type equality is exactly the property being checked.

## Deferred, not dropped

- **Playwright smoke test**: the brief marks this "if time allows." Given
  the scope already delivered (full data layer, layout engine, filters,
  drawer, accessibility, unit tests for the two explicitly required
  surfaces), it wasn't built this phase. `npm run build` + `npm run
  test` + a manual dev-server check stand in for now.
- **Component tests beyond NodeCard and graphMapping**: the brief's literal
  ask was tests for "the node card and the graph data mapping," both
  covered. `OrgChart`, `OrgChartPage`, `DetailDrawer`, `FilterBar`, and the
  API client/query hooks don't have dedicated unit tests yet - they're
  more integration-shaped (data fetching, DOM composition) and are exactly
  what a Playwright smoke test would cover more naturally than mocking
  `fetch` for each. Coverage numbers reported by `npm run test:coverage`
  reflect only files touched by the existing tests, not the whole `src/`
  tree - not a claim of full frontend coverage.
- **elkjs bundle size**: the production bundle is ~1.8MB
  (gzip ~550KB), almost entirely elkjs's layout engine. Acceptable for a
  portfolio demo; a real deployment would code-split it behind a dynamic
  `import()` so the initial shell loads without it.
