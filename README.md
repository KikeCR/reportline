# Reportline

A multi-tenant org chart service: model an organization as a DAG of
reporting lines (solid + dotted, including dual-manager and vacant
positions), sync it from mock HRIS sources, and browse it in a React
viewer. Built as a portfolio project, run locally only (no deploy target).

See `CLAUDE.md` for the architecture rules this codebase follows, and
`docs/adr/` for the reasoning behind the non-obvious decisions - what
SaveState conventions were mirrored vs. deliberately deviated from, why the
graph is shaped the way it is, how the API contract pipeline works, and how
the frontend's design system was chosen.

## Architecture at a glance

```
web/ (React + Vite, TanStack Query, elkjs)
  │  fetch, Zod-validated, X-Org-Id header
  ▼
api/ (Flask, flask-openapi3)
  routes/  → thin: parse, call one service, return an out-model
  services/ → org graph, sync, permissions-free (see "What's simplified")
  repos/   → the only layer that touches pymongo; every query is org_id-scoped
  │
  ▼
MongoDB (replica set - transactions + $graphLookup need one)
  positions / employees / assignments / organizations / quarantine / sync_runs
```

- **The graph** lives in `positions.reports_to` (solid + dotted edges).
  `solid_manager_ids` and `ancestor_ids` are precomputed on every edit so
  reads (subtree lookups, permission-style scoping) are single indexed
  queries instead of a live graph walk - see ADR 0001.
- **The contract**: `api/openapi.json` is generated from the Flask routes,
  never hand-edited; `web/src/api/schema.d.ts` is generated from that; a
  test fails if either drifts. See ADR 0002.
- **Sync**: two fixture-backed adapters (`workday_like`, `bamboo_like`)
  normalize into positions/employees/reporting-lines in two passes, so a
  reporting line can reference a person the first pass hasn't reached yet.
  Bad or unresolvable records are quarantined, never fail the whole run.

## Running it locally

Backend:

```bash
cd api
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp ../.env.example .env   # fill in SECRET_KEY; MONGODB_URI must point at a reachable replica set
.venv/bin/python -m migrations
.venv/bin/python -m scripts.seed
FLASK_APP=app .venv/bin/python -m flask run --port 5001
```

A local dev Mongo (single-node, replica-set-enabled, no auth) can be started with:

```bash
docker run -d --name reportline-dev-mongo -p 27017:27017 mongodb/mongodb-atlas-local:latest
```

then set `MONGODB_URI=mongodb://localhost:27017/reportline?directConnection=true` in `api/.env`.

Frontend:

```bash
cd web
npm install
npm run dev   # proxies /api/v1, /healthz, /readyz to localhost:5001
```

Open the printed Vite URL - the "Tenant" dropdown in the header lists every
seeded organization and auto-selects the first one, so the chart loads with
no setup. Switch tenants from that dropdown; the "Admin" tab (top left) has
the HRIS sync + quarantine tables.

Run the checks:

```bash
make test   # backend: spins up its own MongoDB container per run
make lint   # backend: ruff + mypy strict
cd web && npm run lint && npm run typecheck && npm run test
```

### Or via Docker Compose

```bash
docker compose up --build          # mongo + api + web
docker compose run --rm seed       # migrate + seed, one-off
```

`web` is served by nginx on :5173, proxying `/api/v1` to `api:8000` inside
the compose network - open http://localhost:5173. Mongo here is
unauthenticated (single-node replica set), for local simplicity only - see
"What's simplified" below.

### Kubernetes (demonstration only - no real cluster)

```bash
kubectl kustomize k8s/base   # renders the manifests; nothing to apply them to
```

## API

All endpoints are under `/api/v1` except `/healthz`/`/readyz`. Every
tenant-scoped route reads an `X-Org-Id` header (no auth - see "What's
simplified").

| Method | Path | |
|---|---|---|
| GET | `/healthz`, `/readyz` | liveness / Mongo readiness |
| GET | `/organizations/` | the tenant directory (no header - this is how a client finds its org id) |
| GET | `/org/graph?view=positions\|people&as_of=YYYY-MM-DD` | the full tenant graph |
| GET | `/org/positions/{id}` | a position |
| GET | `/org/positions/{id}/descendants` | solid-line subtree |
| POST, DELETE | `/org/reporting-lines` | add / remove a reporting line |
| GET | `/employees/{id}` | an employee, full view (no field-level gating - see below) |
| POST | `/admin/sync/{source}` | run a sync (`workday_like` or `bamboo_like` fixture data) |
| GET | `/admin/sync/runs` | past sync run counts/duration |
| GET | `/admin/quarantine` | records a sync couldn't resolve, and why |

Every error response is `{"error": "<code>", "message": "...", "details": {...}}`.

The "Admin" tab in the UI runs a sync and shows both tables live. The two
adapters read from fixture files (`api/app/integrations/fixtures/`), not a
live HRIS - each includes deliberately messy records (a missing email, an
unresolved manager reference, a manager cycle) to exercise quarantine.

## What's simplified, and why

This was built in phases with a human reviewing and redirecting scope along
the way - these are the deliberate cuts, not gaps that went unnoticed:

- **No auth.** No JWT, no login, no roles, no manager-subtree permission
  filtering. `X-Org-Id` (picked from a dropdown, no credentials) is the only
  tenant scoping, and every request sees everything in that tenant,
  including compensation. The seam for adding real auth later is narrow by
  design: replace how `useOrg`/`X-Org-Id` are populated on both sides, and
  every call site downstream is unaffected.
- **No LLM feature.** The brief's natural-language "ask" endpoint wasn't built.
- **Docker/Kubernetes/CI exist but are minimal.** `k8s/base` has just
  Deployment/Service/ConfigMap/Secret for api and web - no Ingress, HPA, or
  environment overlays - verified with `kubectl kustomize` only, since there's
  no real cluster to apply it to. CI is two path-filtered GitHub Actions
  workflows (`backend-ci.yml`, `frontend-ci.yml`); there's no preview-deploy
  workflow.
- **Test coverage matches what was explicitly asked for**, not maximal
  coverage: the org-graph invariants (cycles, concurrency, tenant isolation)
  and the sync pipeline are tested against a real MongoDB replica set, and
  the frontend's explicitly-required surfaces (the node card, the graph
  data mapping) have unit tests - but there's no Playwright end-to-end
  suite, and components like the filter bar or admin tables don't have
  dedicated tests.

## How this was built

Built with Claude Code, working from a long, detailed brief that specified
the phases, the MongoDB/testing/API-contract standards, and a sibling
codebase (SaveState) to mirror conventions from. A few things worth naming:

- **`CLAUDE.md`** (architecture rules, layering, the "Don't" list) was
  written before any application code, and enforced throughout - e.g. the
  "every repo query must include org_id" rule is structural (`ScopedRepo`),
  not a convention someone has to remember.
- **ADRs over ad hoc comments** for anything non-obvious: why `ancestor_ids`
  is precomputed, why `flask-openapi3`'s validation callback has to return
  a bare `Response` and not a tuple (found by a route test actually
  exercising it, not by reading the docs), why the org-chart's department
  colors are a text-first accent rather than a fill.
- **Correcting course mid-build**: the initial plan (Phases 4-8 in full)
  produced more ceremony than the project needed for a portfolio piece -
  full ADRs per phase, exhaustive test suites, an eventual auth/roles
  system. Descoping happened live, in conversation, and is recorded above
  rather than silently dropped.
- **A real bug the tooling caught**: this README's first CI run failed
  because the frontend's Node version was pinned to 20 in
  `frontend-ci.yml`, while local development had moved to Node 24 - `jsdom`
  needed a newer built-in `webidl` API that Node 20 doesn't have. Fixed by
  matching CI to the locally-proven version instead of guessing.
