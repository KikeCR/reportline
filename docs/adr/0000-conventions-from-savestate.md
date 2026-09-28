# 0000 - Conventions adopted from SaveState

## Status

Accepted

## Context

Reportline is built to mirror the engineering conventions of the sibling
project `../savestate-kb/` (a Flask + Postgres app) wherever those
conventions transfer cleanly, and to deviate deliberately where MongoDB, the
org DAG, multi-tenancy, or JWT-based roles genuinely require a different
approach. This ADR records what was found in SaveState and, convention by
convention, whether Reportline follows it, adapts it, or replaces it - and
why.

SaveState was read in full (backend, frontend, tests, Docker, CI, lint/format
config, README) on 2026-09-28. No file in SaveState was modified.

## Decision

### 1. Structure and layering

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| `backend/app/{routes,services,models}` - models double as the data-access layer (SQLAlchemy `db.Model` subclasses); routes sometimes query models directly, bypassing services | `api/app/{routes,services,repos,models}` - `models/` is Pydantic only; `repos/` is a new, dedicated data-access layer | **Deviation, required by the Mongo/tenancy contract.** SQLAlchemy models can safely double as the query layer because the ORM already scopes every query to a table with FK constraints. Raw `pymongo` has no such guardrail, and CLAUDE.md's non-negotiable rule is "every repo query MUST include `org_id`." That rule needs one narrow, auditable place to live - `repos/`, built on a `ScopedRepo` base - so it can't be bypassed the way SaveState's routes occasionally bypass its service layer. This is also a correction of a gap the research flagged in SaveState itself (`entries.py` querying `UserGameEntry` directly).
| `app/__init__.py: create_app()` factory; extensions declared unbound in `extensions.py`, bound in the factory | Same pattern: `app/__init__.py: create_app()`; `db.py` holds one process-wide `MongoClient` bound at factory time | No deviation - this is standard Flask and transfers directly. The one addition is that MongoDB standards mandate a single `MongoClient` per process with explicit pool/timeout settings, which SaveState's Postgres connection (managed by SQLAlchemy's pool) didn't need to spell out itself.
| `frontend/src/{api,components,context,hooks,pages,styles,utils,test}` | `web/src/{api,features,...}` using a feature-folder split (`features/orgchart`, `features/admin`) rather than SaveState's flat `pages/`+`components/` | **Deviation, scale-driven.** SaveState is a handful of pages sharing simple components. Reportline's org-chart canvas, admin sync/quarantine views, and ask-box are each a cluster of graph-layout, data-mapping, and UI code that belongs together. Shared primitives still live in a top-level `components/`-equivalent; the split only applies to page-sized features. `api/`, `context`(-equivalent via TanStack Query + auth context)`, `hooks`, `test` all carry over unchanged.
| No repository-wide `docs/` folder; rationale lives in code comments and the README | `docs/adr/`, `docs/data-model.md`, `docs/access-patterns.md`, `docs/runbook.md` | **New practice, not a continuation.** SaveState's comment-driven rationale style works at its size; Reportline's MongoDB standards (access-patterns-before-schema, index justification, migration discipline) require documents that are reviewed and updated in the same PR as schema changes, which a scattered-comments approach can't support.

### 2. App factory, config, environment

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| `config.py` is a plain class reading `os.environ.get(...)` with inline defaults; only `SECRET_KEY` is validated at startup | `config.py` uses `pydantic-settings` (`BaseSettings`) - every variable typed and validated at import time, startup fails fast on a missing/malformed value | **Deviation, required by CLAUDE.md's general code-quality bar** ("pydantic-settings for validated configuration"). SaveState's silent-default approach was flagged in the research as a real gap ("unset/placeholder values aren't caught at startup"); Reportline closes it rather than copying it.
| `.env.example` grouped by concern with comment headers, secrets left blank, non-secrets given real defaults | Same grouping/commenting style, same blank-secret / real-default convention | No deviation - this convention transfers as-is.
| `SCREAMING_SNAKE_CASE` env vars, prefixed per integration (`RAWG_API_KEY`, `DEEPSEEK_*`) | Same style (`MONGODB_URI`, `MONGODB_MAX_POOL_SIZE`, ...) | No deviation. *(A `JWT_*`/`LLM_*` block was planned here too, for Phase 4/7; both were descoped and the unused settings removed from `config.py`/`.env.example` - see §5's correction.)*

### 3. Naming

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| `snake_case.py` modules, `PascalCase` classes, `<Thing>Error` exception names | Same | No deviation.
| Routes: `/api/<plural-resource>`, kebab-case for multi-word action endpoints (`/api/auth/forgot-password`) | `/api/v1/<plural-resource>`, same kebab-case-for-actions rule (`/org/reporting-lines`) | Adds a `/v1` prefix, since CLAUDE.md commits to an explicit API-versioning/breaking-change policy (ADR 0002) that SaveState, a single-consumer app, never needed.
| JSON fields are `snake_case` end-to-end, no camelCase transform layer | Same, end-to-end `snake_case` (`org_id`, `position_id`, `reports_to`) | No deviation - matches the data model in the brief exactly.
| Mongo/Postgres-specific: N/A (SaveState is Postgres, no index-naming convention observed beyond Alembic defaults) | Explicit, descriptive Mongo index names (`ix_positions_org_reports_to`) | New convention, required by the MongoDB standards section - SaveState's Alembic-generated index names weren't a model to follow here.

### 4. Error handling, logging, response format

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| No shared exception hierarchy; every route hand-rolls `jsonify({"error": ...}), status`; two narrow, unrelated custom exceptions (`AlreadyFollowingError`, `LLMConfigError`) | One error taxonomy (`app/errors.py`): a small set of domain exceptions (`NotFoundError`, `ConflictError`, `ForbiddenError`, `ValidationError`, `CycleError`, ...) mapped centrally to HTTP status via a single Flask error handler; every error response is a Pydantic `ErrorOut` | **Deviation, and a fix for a gap the research explicitly flagged** ("won't scale cleanly to a multi-tenant service with more resource types and more failure modes"). CLAUDE.md and Phase 2 both require this ("a single error taxonomy mapped to HTTP responses", documented `ErrorOut` in OpenAPI, specific codes for cycle/forbidden/not-found).
| No structured logging, no request/correlation id; relies on Flask/gunicorn defaults | Structured JSON logging with a request id on every line, plus PyMongo command-monitoring logs for slow queries | **Deviation, and a fix for a flagged gap.** SaveState has no structured logging at all; CLAUDE.md requires it project-wide, and the MongoDB standards require slow-query logging specifically.
| Success responses: bare resource dict, or `{"results": [...]}` for lists; no envelope | Same shape convention: bare Pydantic out-model, or `{"results": [...], "next_cursor": ...}` for cursor-paginated lists | Adapted, not deviated: envelope-free style kept, but pagination is cursor-based (never `skip()`) per the MongoDB standards, so list responses carry a cursor field SaveState's offset-free lists never needed.

### 5. Auth and permissions

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| Flask-Login session cookies, CSRF via Flask-WTF, single implicit "owner" role (`user_id` ownership check), no RBAC | *(planned, not built - see correction below)* JWT bearer tokens (`org_id`, `user_id`, `role`, `position_id` claims), `services/permissions.py` + role decorators, four roles (`org_admin`, `hr_partner`, `manager`, `employee`) | This row describes the Phase 4 design as planned in Phase 0, kept for context. **Superseded 2026-09-28: Phase 4 was descoped entirely** by explicit request ("no auth at all for now... runs as an admin and allows to view all") - there is no JWT, no roles, no `services/permissions.py`, and no "ADR 0003 (tenant scoping and permissions)" (0003 was later used for the frontend org-chart ADR instead, once Phase 3 needed one and Phase 4 no longer did). The only tenant-scoping mechanism is an unauthenticated `X-Org-Id` header, picked from a UI dropdown - see README's "What's simplified, and why". The narrow seam for adding real auth later is documented there.
| Flask-Limiter (Redis-backed) on auth endpoints; flask-talisman security headers, CSP locked to `'none'` | Deferred - not required by any phase in the brief | Not a deviation so much as a scope call: rate limiting and CSP headers are good SaveState patterns worth adopting later, but they're not in the Definition of Done for any phase, so they're left as a documented next step rather than adding unscoped work.

### 6. Testing (mirrors SaveState in framework and layout; diverges only where Mongo forces it)

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| pytest, config in `pyproject.toml` (`testpaths`, `addopts = "-ra --strict-markers"`, `integration` marker) | Same: pytest, same `pyproject.toml` block, same `integration` marker meaning "touches the real database" | No deviation.
| `tests/{models,routes,services}/test_<module>.py` mirroring `app/` 1:1 | `tests/{repos,routes,services}/test_<module>.py` mirroring `api/app/` 1:1 (adds `repos/` where SaveState had none, since models aren't the data layer here) | Adapted to the one structural deviation in §1.
| Real Postgres + Redis via `testcontainers`, autouse fixtures `TRUNCATE ... CASCADE` / `flushdb()` only for tests marked `integration` | Real MongoDB **replica set** (via `testcontainers` or the docker-compose Mongo service), migrations applied in the session fixture instead of `db.create_all()`, autouse per-test database drop/recreate for `integration`-marked tests | **Deviation, required by the brief and by Mongo itself.** `$graphLookup` and multi-document transactions do not work against `mongomock` or a standalone (non-replica-set) `mongod`; the brief is explicit that integration tests must run "against a real MongoDB replica set, never mongomock." Running migrations in the fixture (rather than `create_all()`) is also required because it's the only way the test suite proves the migrations themselves work, per the Definition of Done.
| `tests/factories.py`: plain builder functions, `**overrides`, `itertools.count()` for uniqueness, `expunge()` to detach after commit | Same style: plain builder functions for positions/employees/assignments, `itertools.count()`-based uniqueness, plus a graph-spec-string builder (`"CEO>VP1, CEO>VP2, VP1..VP2"`) the brief asks for, which has no SaveState analogue | Adapted: core builder idiom kept; the graph-spec helper is new because SaveState has no graph-shaped domain to build fixtures for. `expunge()` has no Mongo equivalent (no unit-of-work session to detach from) and is simply dropped.
| `logged_in_client` fixture injects the session directly (`sess["_user_id"] = ...`) rather than calling the login endpoint | *(planned, not built)* | **Superseded along with §5's auth row**: no such fixture exists - there is no login, session, or JWT to fast-path around, since Phase 4 was descoped. Every test that needs tenant scoping just passes an `org_id` directly.
| `requests_mock`-based fixtures for third-party HTTP (RAWG, LLM) | Same idea for `integrations/` adapters (workday_like, bamboo_like fixture payloads) and `llm/openai_compatible.py` (or the `llm/fake.py` deterministic provider for most tests) | No deviation in spirit; SaveState's dual-function idiom (raising core call + non-raising `try_` wrapper) is explicitly adopted for the LLM and integration adapters too (see §9).
| Coverage: **enforced on frontend** (`lines/statements/functions: 80, branches: 75` via `@vitest/coverage-v8`), **not enforced on backend** (`pytest-cov` runs in CI with no `--cov-fail-under`) | Frontend: keep SaveState's exact thresholds (80/80/80/75). Backend: enforce **85% on `services/` and `repos/`** via `--cov-fail-under` in CI | Per the brief's own instruction ("if SaveState has a coverage threshold, use it; if not, enforce at least 85%") applied per-side: frontend already has one, so it's kept as-is; backend has none, so the 85% floor is added - directly fixing a gap the research flagged.
| Backend: no Makefile, raw `pytest`/`docker compose exec` commands documented in the README | `make test`, `make lint`, `make migrate`, etc. (full list in CLAUDE.md) | **Deviation, required by the brief**, which specifies exact Makefile targets. SaveState's choice not to have one was a valid option for its size; Reportline's spec mandates one explicitly.
| Frontend: Vitest, co-located `*.test.tsx`, Page Object pattern (`src/test/page-objects/`), `vi.mock` on the API client | Same runner, same co-location, same Page Object pattern for the graph canvas/node card/admin views, same API-client mocking approach | No deviation - this is a strong, consistently-applied SaveState convention and transfers directly.

### 7. Docker, Compose, CI

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| Backend Dockerfile: single-stage, non-root `appuser`, gunicorn default `CMD`. Frontend Dockerfile: single-stage, dev-server only (`npm run dev`), no production build/serve stage | `api/Dockerfile`: multi-stage, non-root user, gunicorn, healthcheck. `web/`: build stage + small static-server/nginx stage | **Deviation, required by the brief and by the missing piece the research flagged** ("no example of a production-grade static frontend image to copy from"). Phase 6 explicitly asks for a multi-stage API image and a real static/nginx stage for web, since k8s needs a real production image for both.
| `docker-compose.yml`: Postgres with plain user/password, no replica set, no auth complexity beyond that | *(planned: replica set with keyfile auth and least-privilege users - see correction)* A single-node Mongo replica set (`mongodb/mongodb-atlas-local:latest`), **no auth at all** | **Deviation from SaveState, required by MongoDB standards** for the replica-set part (transactions and `$graphLookup` need one; SaveState's single-node Postgres had no equivalent requirement). **Superseded on the auth part**: the keyfile-auth/least-privilege-users design planned here was never built - `docker-compose.yml` runs Mongo with no auth, a deliberate local-simplicity call documented in that file's own header comment, consistent with Phase 4's broader descoping.
| Custom bash git hook (`.githooks/pre-commit`, activated via `core.hooksPath`), scoped to staged files per side | Same mechanism: custom `.githooks/pre-commit`, same staged-files-per-side scoping, running `ruff` on `api/` and lint/format on `web/` | No deviation - this is a clean, working convention and the brief's "pre-commit hooks" requirement doesn't mandate the `pre-commit` framework specifically.
| Ruff only, minimal rule set (`select = ["E", "F", "I"]`), no mypy anywhere | Ruff with a broader rule set (adds `B` bugbear, `UP` pyupgrade, at minimum) **and mypy strict on `api/app`** | **Deviation, required by CLAUDE.md** ("mypy strict on api/app"). SaveState has zero type-checking on the backend; Reportline's brief commits to strict typing as a core rule, not an optional nicety.
| Frontend: Prettier only (tabs, no semicolons, single quotes), explicitly **no ESLint**; `tsc -b` intentionally left out of `npm run build` and out of CI | Keep SaveState's exact Prettier config. **Add ESLint** (typescript-eslint recommended + react-hooks rules + prettier-compat) and **wire `tsc -b` into `make types`/CI** | **Deviation, and a fix for two gaps the research flagged explicitly** (no lint beyond formatting; type errors can ship silently because `tsc` isn't in CI). A graph-layout-heavy app with async data fetching (TanStack Query, `elkjs` effects) benefits from `react-hooks/exhaustive-deps` and floating-promise-style lint rules that Prettier can't provide. Prettier's exact style (tabs, no semi, single quote) is kept as-is for consistency with the sibling project.
| Two independent, path-filtered CI workflows (`backend-tests.yml`, `frontend-tests.yml`); no CD at all | **Kept as two independent workflows**: `backend-ci.yml` (ruff, mypy, pytest with coverage against a Mongo replica-set service via testcontainers, OpenAPI drift check, api docker build) and `frontend-ci.yml` (ESLint + Prettier check, `tsc -b`, Vitest + coverage, web docker build) | **No deviation on the split** (corrected 2026-09-28: an earlier draft of this ADR consolidated both sides into one `ci.yml`; the user asked explicitly for one pipeline per side, which is just SaveState's own convention - the initial consolidation was an unforced deviation and has been reverted). **Superseded 2026-09-28: no `preview.yml`, no CD.** A third per-PR-preview workflow was planned here but Phase 6's deploy/preview-environment scope was cut ("this will be only run locally for now") - there is no CD at all, matching SaveState. The two CI workflows' contents still deviate from SaveState's, since Phase 2's contract-drift gate has no SaveState analogue.

### 8. Documentation style

| SaveState convention | Reportline equivalent | Deviation and why |
|---|---|---|
| Single root README: pitch, Features, Stack table, Prerequisites, Setup, "Development notes" (gotchas), a deep-dive section for the one complex feature, an annotated project-structure tree, attribution. No Limitations/Next-steps section, no architecture diagram | Same skeleton, plus a mermaid architecture diagram, a features-to-concepts table, and an explicit "honest limitations and next steps" section and a "How I built this with Claude Code" section | Adapted: SaveState's structure and tone (terse, why-not-just-what, inline gotchas) are kept. The additions are required by Phase 8 of the brief, which SaveState's simpler, single-audience README never needed.
| Rationale lives in code comments; no ADRs | *(planned: `0001`-`0005`, org-as-dag / api-contract / tenant-scoping / sync-conflict-rules / llm-safety - see correction)* Actually written: `docs/adr/0001-org-as-dag.md`, `0002-api-contract.md`, `0003-frontend-org-chart.md` | New practice per §1 - not a continuation of a SaveState habit. **Superseded 2026-09-28**: only three ADRs beyond this one exist. `tenant-scoping` was never written because Phase 4 was descoped (see §5); `sync-conflict-rules` was never written because the conflict rule turned out simple enough to document as a docstring in `services/sync.py` instead, once "less ceremony" was requested; `llm-safety` was never written because Phase 7 (the LLM "ask" feature) was descoped. `0003` was reassigned to the frontend org-chart design once Phase 3 needed an ADR and Phase 4 no longer did.

### 9. Idioms worth carrying over unchanged

Two SaveState patterns are strong, reusable, and have no reason to be deviated from - they're adopted as-is rather than appearing in either "gap" or "deviation":

- **Raising core + safe `try_`-prefixed wrapper** for external calls (SaveState's `chat_completion_json` / `try_chat_completion_json`, used to walk a provider fallback chain). Reportline's `llm/` provider interface and `integrations/` adapters use the same idiom.
- **Page Object pattern** for frontend component/page tests (`src/test/page-objects/`), with a shared `renderWithProviders` helper. Reportline's frontend tests use the same pattern for the graph canvas, node card, and admin views.

## Consequences

- Every place Reportline's structure, tooling, or process differs from SaveState is traceable to one of: a MongoDB/DAG technical requirement, an explicit instruction in the engagement brief (CLAUDE.md, a named phase), or a gap the SaveState research itself flagged as worth fixing rather than copying. None of the deviations above are arbitrary preference.
- The `repos/` layer, the Mongo migration runner, and the ADR/docs discipline are all net-new design work with no SaveState precedent to lean on - these get their own ADRs (0001-0003; see the correction in §8 for why there's no 0004/0005 and no separate auth ADR) as they're built, rather than being justified here.
- Where SaveState left a gap (no backend coverage threshold, no error taxonomy, no structured logging, no lint beyond formatting, `tsc` not wired into CI, dev-only frontend image), Reportline closes it from Phase 1 onward rather than inheriting it, since the brief's Definition of Done requires it either directly or via CLAUDE.md's code-quality bar.
