# CLAUDE.md

Guidance for working on Reportline. This file governs the whole project; if
something here conflicts with a later request, flag the conflict rather than
silently picking one.

## Purpose

Reportline is a multi-tenant org chart service. It models an organization as
a DAG of positions (solid and dotted reporting lines), tracks who occupies
each position over time, and serves a tenant-scoped, role-aware org chart to
a React frontend. It ingests data from mock HRIS sources (Workday-like,
BambooHR-like), quarantines bad records instead of failing a whole sync, and
exposes a natural-language "ask" endpoint that translates questions into
validated, permission-scoped filters - never into raw queries.

Built as a portfolio project mirroring the engineering conventions of the
sibling project `../savestate-kb/`; every deliberate deviation from those
conventions is recorded in `docs/adr/0000-conventions-from-savestate.md`.

## Stack

- **API**: Python, Flask (app-factory pattern), `flask-openapi3` for OpenAPI
  generation from Pydantic v2 models, `pydantic-settings` for config.
- **Database**: MongoDB (replica set, even locally - transactions and
  `$graphLookup` require it), accessed only through `pymongo` in `repos/`.
- **Auth**: JWT bearer tokens (`org_id`, `user_id`, `role`, `position_id`
  claims). No sessions, no cookies.
- **Web**: Vite + React + TypeScript (strict), TanStack Query, `elkjs` for
  graph layout, Zod for response validation at the API boundary.
- **LLM**: provider-agnostic interface (`llm/`) with an OpenAI-compatible
  implementation and a deterministic fake for tests/offline demos.
- **Infra**: Docker Compose locally (Mongo replica set with keyfile auth),
  Kubernetes manifests (Kustomize overlays) for dev/preview, GitHub Actions
  for CI and PR preview environments.

## Commands

| Command | Does |
|---|---|
| `make dev` | Bring up the full stack (Mongo replica set, api, web) from a clean clone |
| `make test` | Run the full backend + frontend test suites (what CI runs) |
| `make lint` | Ruff (lint + format check) on `api/`, ESLint + Prettier check on `web/`, mypy strict on `api/app` |
| `make openapi` | Regenerate `api/openapi.json` (deterministic, sorted) |
| `make types` | Regenerate `web/src/api/schema.d.ts` from `api/openapi.json` |
| `make migrate` | Apply pending Mongo migrations |
| `make migrate-status` | Show applied/pending migrations |
| `make seed` | Run the deterministic, idempotent seed script |

## Architecture rules

These are load-bearing, not stylistic preferences:

1. **Routes are thin.** A route parses and validates input with a Pydantic
   in-model, calls exactly one service function, and returns a Pydantic
   out-model. No query logic, no business rules in `routes/`.
2. **Business logic lives in `services/`.** Only `repos/` may import
   `pymongo` collections or issue queries. A service never touches a
   `pymongo.collection.Collection` directly.
3. **Every repo query MUST include `org_id`.** No exceptions. This is
   enforced structurally through `ScopedRepo` - a repo method that queries
   without a tenant scope is a bug, not a style issue.
4. **Never return raw Mongo documents.** Every response is mapped to an
   out-model. Sensitive fields (compensation) exist only on HR-level
   out-models (`EmployeeHROut`), never on `EmployeePublicOut`.
5. **Graph edits go through `services/org_graph.py` only.** Cycle checking,
   primary-edge enforcement, and `ancestor_ids` recomputation live there and
   nowhere else.
6. **Generated files are never hand-edited.** `api/openapi.json` and
   `web/src/api/schema.d.ts` are regenerated, not patched.
7. **Changing an API model requires regenerating OpenAPI and TS types in the
   same PR.** CI fails on drift.
8. **Schema, validators, and indexes change only through a new migration**
   in `api/migrations/`. Application startup and request-handling code never
   call `create_index` or `collMod`.
9. **Follow `docs/adr/0000-conventions-from-savestate.md`.** Tests mirror
   SaveState's framework, layout, fixture, and naming conventions unless
   that ADR records a deliberate deviation.
10. **Update `docs/data-model.md` and `docs/access-patterns.md` in the same
    PR as any schema or query change.** They must always match the
    migrations exactly.
11. **AI-generated code gets the same review bar as human code.** Check
    specifically for invented library APIs, missing tenant scoping,
    swallowed exceptions, and tests that assert nothing.

## Don't

- Don't call `create_index`, `collMod`, or `create_collection` outside a
  migration.
- Don't query a Mongo collection anywhere outside `repos/`.
- Don't return a raw `dict` from `pymongo` (or a bare Mongo document) from a
  route or service - always map to a Pydantic out-model first.
- Don't hand-edit `api/openapi.json` or `web/src/api/schema.d.ts`.
- Don't use `skip()` for pagination on a collection that can grow - use
  cursor-based pagination.
- Don't store money as `float` - use `Decimal128` plus a currency code.
- Don't invent a library API. If unsure how something works, read the docs
  or installed source and say so before writing code against it.
- Don't leave a TODO without a corresponding entry in the README's
  next-steps section.
- Don't use `mongomock` for repo/route integration tests - they run against
  a real MongoDB replica set (see ADR 0000, §6).
- Don't add scope beyond what the current phase asks for. This project is
  meant to be finished and demoable, not sprawling.
