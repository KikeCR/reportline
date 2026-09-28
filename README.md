# Reportline

A multi-tenant org chart service. See `CLAUDE.md` for architecture rules and
`docs/adr/` for design decisions. Full setup, screenshots, and demo story
land in Phase 8 - this section covers what's actually running today
(Phase 1: backend core and the org graph).

## Status

- Phase 0: SaveState conventions ADR - done (`docs/adr/0000-conventions-from-savestate.md`)
- Phase 1: Backend core and the org graph - done
- Phases 2-8: not started yet

## Backend quickstart (Phase 1)

```bash
cd api
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

```bash
make test    # spins up its own MongoDB replica-set container per test run
make lint    # ruff + mypy strict
```

Running the migrations or the seed script against a real dev database
requires `MONGODB_URI` and `SECRET_KEY` (see `.env.example`) - there's no
docker-compose Mongo yet (that's Phase 6), so point `MONGODB_URI` at any
MongoDB replica set you have locally in the meantime:

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

## Known deferrals (not TODOs left in code - tracked here per CLAUDE.md)

- `org_graph.get_graph(org_id)` doesn't yet take `as_of` or `viewer_scope`,
  though the brief's Phase 1 spec lists them. Both need machinery this
  phase doesn't build: `as_of` needs the `/org/graph?view=people` route to
  exist (Phase 2) before there's a caller that joins in assignment
  occupancy, and `viewer_scope` needs the permission model (Phase 4). Adding
  unused parameters now would just be dead code; the signature grows when
  Phase 2/4 give it a real caller.
- No docker-compose Mongo yet (Phase 6) - `make migrate`/`make migrate-status`/
  `make seed` need a `MONGODB_URI` you provide yourself until then.
