# Reportline

A multi-tenant org chart service, run locally (no deploy target). See
`CLAUDE.md` for architecture rules and `docs/adr/` for design decisions.

## Status

- Phase 0-2: SaveState conventions, backend core/org graph, API + contract pipeline - done
- Phase 3: React org chart viewer - done
- Phase 4: **simplified by request** - no auth/roles/JWT. The app runs
  fully open (every request has admin-level visibility, including
  compensation) - see "Descoped" below.
- Phase 5: HRIS sync adapters + quarantine - done
- Phase 6: Docker/K8s manifests/CI - done, kept intentionally minimal (no
  real cluster or deploy target - see "Running it locally" and "Descoped")
- Phase 7 (LLM "ask" feature): **skipped by request**
- Phase 8: this README is the polish pass, kept intentionally light

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

Open the printed Vite URL, paste a seeded org id (printed by `scripts.seed`,
or check Mongo directly) into the "Tenant id" field, and the chart loads.

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
the compose network - open http://localhost:5173. Mongo here is unauthenticated
(single-node replica set), for local simplicity only - see "Descoped".

### Kubernetes (demonstration only - no real cluster)

```bash
kubectl kustomize k8s/base   # renders the manifests; nothing to apply them to
```

## API

All endpoints are under `/api/v1` except `/healthz`/`/readyz`. Every
tenant-scoped route reads an `X-Org-Id` header (no auth - see "Descoped").

| Method | Path | |
|---|---|---|
| GET | `/healthz` / `/readyz` | liveness / Mongo readiness |
| GET | `/api/v1/org/positions/{id}` | a position |
| GET | `/api/v1/org/positions/{id}/descendants` | solid-line subtree |
| GET | `/api/v1/org/graph?view=positions\|people&as_of=YYYY-MM-DD` | the full tenant graph |
| POST` / `DELETE` | `/api/v1/org/reporting-lines` | add / remove a reporting line |
| GET | `/api/v1/employees/{id}` | an employee, full view (no field-level gating - see "Descoped") |
| POST | `/api/v1/admin/sync/{source}` | run a sync (`workday_like` or `bamboo_like` fixture data) |
| GET | `/api/v1/admin/sync/runs` | past sync run counts/duration |
| GET | `/api/v1/admin/quarantine` | records a sync couldn't resolve, and why |

Every error response is `{"error": "<code>", "message": "...", "details": {...}}`.

The "Admin" tab in the UI runs a sync and shows both tables live. The two
adapters read from fixture files (`api/app/integrations/fixtures/`), not a
live HRIS - each includes deliberately messy records (a missing email, an
unresolved manager reference, a manager cycle) to exercise quarantine.

## Descoped by request, not forgotten

- **Auth/roles/permission scoping (original Phase 4)**: not built. No JWT,
  no login, no `org_admin`/`hr_partner`/`manager`/`employee` roles, no
  manager-subtree filtering. `X-Org-Id` (a plain header, entered by hand in
  the UI) is the only scoping - every request sees everything in that
  tenant, including employee compensation. Add real auth later by
  replacing how `X-Org-Id`/`useOrg` are populated; every call site already
  goes through that one seam.
- **Kubernetes/CI (Phase 6)**: built, but minimal by request - `k8s/base`
  has just Deployment/Service/ConfigMap/Secret for api and web (no Ingress,
  HPA, or overlays), verified with `kubectl kustomize` only (no cluster to
  apply to). CI is two path-filtered GitHub Actions workflows
  (`backend-ci.yml`, `frontend-ci.yml`) with no preview-deploy workflow.
- **LLM "ask" feature (original Phase 7)**: not built.
- **Playwright smoke test / full frontend component coverage**: the brief's
  explicit ask (NodeCard + graph data mapping tests) is covered; broader UI
  integration tests weren't added.
