# 0002 - The API contract: generation, versioning, and the interim tenant header

## Status

Accepted

## Context

Phase 2 adds the first real HTTP surface. Three things need deciding before
any route ships: how tenant scoping works before Phase 4's auth exists, how
errors are shaped consistently across every route, and how the OpenAPI
contract is generated, checked for drift, and versioned as it evolves.

## Decision

### `flask-openapi3` request binding, verified against its installed source

Its routing decorators (`.get`/`.post`/`.delete`) bind a Pydantic model to a
route's `header`/`path`/`query`/`body` parameter **by the parameter's name**,
not by a special marker type - a view function `def f(path: X, header: Y)`
gets `X`/`Y` instantiated from the request automatically. This was read
directly from `flask_openapi3/request.py` and `scaffold.py` in the installed
package before writing a single route, per CLAUDE.md's "never invent a
library API" rule. Two behaviors worth recording because they weren't
obvious from the constructor signatures alone:

- A route's return value is **not** auto-serialized from a returned Pydantic
  model - it's passed straight through as a normal Flask return value. Every
  route here does `out_model.model_dump(mode="json")` (a dict, which Flask's
  own dict-to-JSON auto-conversion handles) rather than returning the model
  itself.
- `validation_error_callback` must return a single `Response` object, not a
  `(body, status)` tuple - flask-openapi3 passes the callback's return value
  straight into `werkzeug.abort()`, which only special-cases a bare
  `Response`. A tuple raises `LookupError: no exception for (...)` inside
  `abort()`. This was caught by a route test
  (`test_get_position_422s_for_a_malformed_header`) actually exercising the
  callback against a live Flask test client, not by reading the source
  alone - a good example of why "at least one test per endpoint" catches
  what code review of framework glue code might not.

### Tenant scoping before auth exists: `TenantHeader`

Every tenant-scoped route reads `header: TenantHeader` (`app/models/api/common.py`),
a single `x_org_id` field that flask-openapi3 matches to the `X-Org-Id`
request header. This is deliberately not a path or query parameter, for one
reason: **Phase 4 replaces this with a JWT claim, and both mechanisms read
the tenant off a header** (`X-Org-Id` now, `Authorization: Bearer ...`
later). Every route already calls `header.x_org_id` - Phase 4's change is
contained to how that one field is populated, not to any route body. A
missing or malformed header is a `422 validation_error` for now (there's no
`401` in the taxonomy yet - Phase 4 introduces one alongside real
authentication).

### One error format, including framework-level validation failures

CLAUDE.md requires a single, documented `ErrorOut` shape. Two error sources
exist and both are normalized to it:

1. Domain errors (`app.errors.ReportlineError` and its subclasses -
   `NotFoundError` 404, `ForbiddenError` 403, `ConflictError`/`CycleError`/
   `ConcurrentGraphEditError` 409, `DomainValidationError` 422) are mapped by
   one Flask error handler (`app/__init__.py:_handle_reportline_error`).
2. flask-openapi3's own request-validation failures (malformed path/query/
   header/body against the declared Pydantic model) default to returning
   raw Pydantic `ValidationError.json()` output, not `ErrorOut`. A custom
   `validation_error_callback` (`_handle_validation_error`) normalizes these
   to the same `ErrorOut` shape (`error: "validation_error"`, `message`: the
   first error's message, `details.errors`: the full Pydantic error list) so
   a client never has to branch on which of the two validation paths fired.

### List responses use an envelope, not a bare array

`responses={200: list[SomeModel]}` isn't a form flask-openapi3's `responses`
dict accepts (it expects `Type[BaseModel] | dict | None` per its signature -
a bare generic `list[...]` isn't a `BaseModel` subclass). Rather than work
around that, list endpoints use an envelope model (`DescendantsOut.results:
list[DescendantOut]`), which also happens to match the `{"results": [...]}`
convention already kept from SaveState (ADR 0000, §4) - no separate
decision needed, the framework constraint and the existing convention point
the same way.

### `get_descendants`/`get_ancestors` now distinguish "empty" from "not found"

Building the routes surfaced a real gap from Phase 1: `org_graph.get_descendants`
and `get_ancestors` silently returned `[]` for a position that doesn't exist
at all, indistinguishable from a real position with no descendants/ancestors
(a leaf, or a root). `GET /org/positions/{id}/descendants` on an unknown id
needs to 404, not 200 with an empty list - both functions now check
existence first and raise `NotFoundError`, with tests for both the
not-found case and the legitimately-empty case so the distinction doesn't
regress silently.

### `get_graph`'s `view="people"` join, and why it lives in `org_graph.py`

Phase 1's ADR 0001 deferred `as_of`/`view` on `get_graph` for lack of a
caller; Phase 2's `/org/graph` route is that caller, so they're added now
rather than staying stubbed. The occupant join (position -> current/as-of
assignment -> employee name) lives in `services/org_graph.py`, not in the
route: CLAUDE.md draws the line at "business logic lives in services", and
joining three tenant-scoped repos to answer "who sits here" is exactly that,
not routing. It batches employee lookups (`EmployeeRepo.get_many_by_ids`)
across the whole graph rather than querying per-node, to keep `GET
/org/graph?view=people` at a small constant number of queries regardless of
headcount. `viewer_scope` (permission filtering) is still deferred - Phase 4
adds it as a wrapper once a permission model exists to filter by.

### OpenAPI generation and the drift check

`scripts/export_openapi.py` builds the full spec from `create_app().api_doc`
and writes it with `json.dumps(..., indent=2, sort_keys=True)` - verified
byte-identical across repeated runs before relying on it. `make openapi`
regenerates `api/openapi.json`; `tests/contract/test_openapi_drift.py` reruns
that generation and fails if it doesn't match the committed file, so drift
is caught by `make test` locally, not just in CI (Phase 6 wires the same
check into `backend-ci.yml`, plus a breaking-change check against the base
branch's committed spec).

### Versioning rules

- The API is served under `/api/v1`. `/healthz` and `/readyz` are
  unversioned infrastructure endpoints (mirroring SaveState's one
  unprefixed `/health` route - ADR 0000, §3).
- **Additive changes** (a new endpoint, a new optional request field, a new
  response field) ship without a version bump - `v1` stays `v1`. The
  contract-drift check still requires `api/openapi.json` to be regenerated
  and committed in the same PR.
- **Breaking changes** (removing/renaming a field, tightening a validation
  rule, changing a status code's meaning, removing an endpoint) require a
  new version prefix (`/api/v2`) that coexists with `/api/v1` rather than
  replacing it in place. The old version is marked deprecated (documented in
  its OpenAPI `description`, not removed from the spec) for at least one
  release cycle before its routes are actually deleted - deprecate, then
  remove, never both at once.
- Phase 6's CI runs an oasdiff-equivalent check comparing the PR's
  `api/openapi.json` against the base branch's, specifically to catch a
  breaking change that was shipped as if it were additive.

### Web client wrapper and `make types`: moved to Phase 3, not dropped

The brief lists a typed fetch client and Zod schemas under Phase 2. Building
that now would mean creating `web/` as a bare API-client shell, then Phase
3 (explicitly asked to get real design-skill attention, not a generic
scaffold) immediately restructuring it once the actual React app exists.
Rather than build it twice, `web/` - including `make types`
(`openapi-typescript` against `api/openapi.json`), the typed client, and the
Zod-vs-generated-types drift test - is created once, at the start of Phase
3, as part of the real frontend scaffold. `api/openapi.json` already exists
and is stable for it to consume whenever Phase 3 starts.

## Consequences

- Every route file is small because the framework quirks above are handled
  once, centrally (`app/__init__.py`'s error handlers, `TenantHeader`) -
  route bodies only ever call one service function and map its result to an
  out-model, per CLAUDE.md's "routes are thin" rule.
- The `X-Org-Id` header is a known, documented placeholder with exactly one
  swap point; anyone reading this ADR before Phase 4 knows it's not a
  long-term auth mechanism.
- `api/openapi.json` is real, committed, generated output (26KB, 7 paths, 16
  schemas as of this phase) with an automated test guaranteeing it can never
  silently drift from the code that generates it.
