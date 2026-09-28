# Reportline

A multi-tenant org chart service. See `CLAUDE.md` for architecture rules and
`docs/adr/` for design decisions. Full setup, screenshots, and demo story
land in Phase 8 - this section covers what's actually running today
(Phase 1: backend core; Phase 2: the API and contract pipeline).

## Status

- Phase 0: SaveState conventions ADR - done (`docs/adr/0000-conventions-from-savestate.md`)
- Phase 1: Backend core and the org graph - done
- Phase 2: API and the contract pipeline - done
- Phases 3-8: not started yet

## Backend quickstart

```bash
cd api
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

```bash
make test     # spins up its own MongoDB replica-set container per test run
make lint     # ruff + mypy strict
make openapi  # regenerates api/openapi.json (needs api/.env - copy .env.example there first)
```

Running the migrations, the seed script, or the live API against a real dev
database requires `MONGODB_URI` and `SECRET_KEY` (see `.env.example`) -
there's no docker-compose Mongo yet (that's Phase 6), so point
`MONGODB_URI` at any MongoDB replica set you have locally in the meantime:

```bash
make migrate
make migrate-status
make seed                                        # deterministic demo data for two tenants
cd api && .venv/bin/python -m scripts.seed --reset  # drop and recreate both tenants
```

`scripts/explain_queries.py` prints index-usage summaries for the key
queries in `docs/access-patterns.md` once seed data exists:

```bash
cd api && .venv/bin/python -m scripts.explain_queries
```

## API (Phase 2)

All endpoints are under `/api/v1` except `/healthz`/`/readyz`. Every
tenant-scoped route reads an `X-Org-Id` header - see
`docs/adr/0002-api-contract.md` for why (it's a documented, single-swap-point
placeholder for Phase 4's JWT, not a long-term auth mechanism).

| Method | Path | |
|---|---|---|
| GET | `/healthz` | dependency-free liveness check |
| GET | `/readyz` | checks MongoDB connectivity |
| GET | `/api/v1/org/positions/{id}` | a position |
| GET | `/api/v1/org/positions/{id}/descendants` | solid-line subtree |
| GET | `/api/v1/org/graph?view=positions\|people&as_of=YYYY-MM-DD` | the full tenant graph |
| POST | `/api/v1/org/reporting-lines` | add a reporting line |
| DELETE | `/api/v1/org/reporting-lines` | remove a reporting line |
| GET | `/api/v1/employees/{id}` | an employee (public view only, for now) |

Every error response is `{"error": "<code>", "message": "...", "details": {...}}`
(`ErrorOut`, documented in `api/openapi.json`), whether it came from a
business-rule rejection or a malformed request.

## Known deferrals (not TODOs left in code - tracked here per CLAUDE.md)

- `EmployeePublicOut` is the only shape `GET /employees/{id}` returns for
  now - `EmployeeHROut` (adds compensation) exists as a model but has no
  route branch to it yet, since that requires Phase 4's role check.
- `org_graph.get_graph`'s `viewer_scope` (permission filtering) isn't
  implemented - it needs Phase 4's permission model to filter by.
- The typed web client + Zod schemas (brief's Phase 2 "web client wrapper")
  move to the start of Phase 3 instead, built alongside the real `web/`
  scaffold rather than as a throwaway shell Phase 3 would immediately
  restructure - see ADR 0002.
- No docker-compose Mongo yet (Phase 6) - `make migrate`/`make migrate-status`/
  `make seed`/the live API need a `MONGODB_URI` you provide yourself until
  then.
