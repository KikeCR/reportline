# Data model

Every collection, its fields, types, constraints, indexes, and the query
each index serves. This must always match `api/migrations/` exactly - a
schema or index change updates this file in the same PR.

## Conventions applied to every collection

- `_id`: `ObjectId`, database-native. Becomes a string at the API boundary
  through one shared `PyObjectId` type (`api/app/models/common.py`) - never
  exposed as an `ObjectId` in a response.
- `org_id`: `ObjectId`, references `organizations._id`. Present on every
  document in every tenant-scoped collection; every query in `repos/`
  includes it via `ScopedRepo`.
- `schema_version`: `int`, starts at `1`. Bumped only alongside a migration
  that changes this collection's shape, per the expand/migrate/contract
  process in `api/migrations/`.
- `created_at`, `updated_at`: BSON `Date`, timezone-aware UTC.
- `created_by`, `updated_by`: `ObjectId | null`, referencing the acting
  user. `null` for records written by `seed.py` or a sync run (Phase 5),
  where CLAUDE.md's auditing rule doesn't yet have an authenticated actor to
  attribute to.

## Addition beyond the brief's Phase 1 list: `organizations`

The brief's Phase 1 collection list is `positions`, `employees`,
`assignments`, `quarantine`. A fifth collection, `organizations`, is added
here and recorded as a deliberate addition (not a deviation from SaveState -
SaveState has no tenant concept at all):

> **Why**: `org_graph.add_reporting_line` must "handle concurrent edits with
> an org-level `graph_version` field" (brief, Phase 1). A field described as
> "org-level" needs an org-level document to live on - there is no
> `organizations` collection in the brief's list to hold it. Rather than
> bolt a global version counter onto an arbitrary position document (which
> would conflate "one position changed" with "the whole org's graph
> changed"), a minimal `organizations` collection is added. It also gives
> JWT's `org_id` claim (Phase 4) something authoritative to validate
> against, and gives the seed script and future admin UI a natural place
> for the tenant's display name.

### `organizations`

| Field | Type | Constraint |
|---|---|---|
| `_id` | `ObjectId` | the org identifier used as `org_id` everywhere else |
| `name` | `string` | required |
| `graph_version` | `int` | starts at `0`; incremented atomically by every `org_graph` mutation |
| `schema_version` | `int` | |
| `created_at`, `updated_at` | `Date` | |

No secondary indexes - every lookup is by `_id`.

## `positions`

| Field | Type | Constraint |
|---|---|---|
| `_id` | `ObjectId` | |
| `org_id` | `ObjectId` | required |
| `title` | `string` | required, 1-200 chars |
| `department` | `string` | required |
| `status` | `string` enum | `"active" \| "vacant" \| "closed"` |
| `reports_to` | `array<{position_id: ObjectId, relation: "solid"\|"dotted", is_primary: bool}>` | **capped at 8 entries** (see below); at most one entry may have `relation: "solid", is_primary: true` |
| `solid_manager_ids` | `array<ObjectId>` | denormalized: exactly the `position_id`s from `reports_to` where `relation == "solid"`. Capped at 8 for the same reason as `reports_to`, since it's a strict subset of it |
| `ancestor_ids` | `array<ObjectId>` | denormalized union of every ancestor reachable via **any** edge type (solid or dotted). Bounded by max graph depth, not fan-out - see `MAX_GRAPH_DEPTH` below |
| `graph_version` | *(none - lives on `organizations`, see above)* | |
| `schema_version`, `created_at`, `updated_at`, `created_by`, `updated_by` | - | standard fields |

**Why `reports_to` is capped at 8, not left unbounded**: the brief requires
capping it ("no unbounded arrays... cap `reports_to` length"). The seed
data's most extreme case is two solid-line co-managers plus a dotted line to
a third (3 entries); 8 gives real headroom for messier real-world org charts
without being unbounded. The cap is enforced both in the `$jsonSchema`
validator (`maxItems: 8`) and in `org_graph.add_reporting_line` before any
write, so the rejection happens with a clean `422`/`409`, not a validator
error surfacing as a raw driver exception.

**Why `ancestor_ids` isn't capped the same way**: it grows with
organizational *depth*, not a position's own fan-out, so an array-length cap
would be the wrong control. Depth is instead bounded by
`MAX_GRAPH_DEPTH = 20` (a constant in `services/org_graph.py`), used as
`$graphLookup`'s `maxDepth` and enforced as a hard ceiling when adding a
reporting line - real organizations don't exceed this, and it protects
against a `$graphLookup` walking a runaway graph if a cycle-check bug ever
let one through.

**Embed vs. reference**: `reports_to` is embedded (a position's own edges
are small, bounded, and always read together with the position). Ancestor
and solid-manager sets are also embedded, as precomputed arrays, rather than
requiring a `$graphLookup` on every read - see `docs/access-patterns.md`'s
"Notes that shaped the schema" for why (the `restrictSearchWithMatch`
pitfall). Employees and assignments are **referenced**, not embedded - a
position's occupant(s) change over time and a position can have zero, one,
or (briefly, per the seed story) two concurrent occupants, which doesn't fit
a fixed embedded shape.

### Indexes

| Name | Keys | Serves | Justification |
|---|---|---|---|
| `ix_positions_org_reports_to` | `{org_id: 1, "reports_to.position_id": 1}` | P4 | find who currently reports to a position across all edge types, before validating a new edge or counting direct reports |
| `ix_positions_org_solid_manager_ids` | `{org_id: 1, solid_manager_ids: 1}` | P5, and is the index MongoDB uses for `$graphLookup`'s `connectToField` during descendant traversal (P2) | this is the hot index - every `get_descendants` call and every graph edit's subtree walk depends on it |
| `ix_positions_org_ancestor_ids` | `{org_id: 1, ancestor_ids: 1}` | P3, P6 | P6 (manager-role permission scoping) runs on nearly every request a `manager` makes - this index is load-bearing for authorization, not just a convenience |
| `ix_positions_org_status` | `{org_id: 1, status: 1}` | P7 | excluding closed positions from the full-graph read |

No index is added for P8 (root positions, `reports_to: {$size: 0}`) - array
size predicates don't use a normal index well, and at per-tenant cardinality
(tens to low thousands of positions) a `{org_id: 1}`-scoped scan is cheap.
Revisit with a materialized `is_root: bool` field if a tenant's position
count ever makes this measurably slow (`scripts/explain_queries.py` is how
that would be caught).

## `employees`

| Field | Type | Constraint |
|---|---|---|
| `_id` | `ObjectId` | |
| `org_id` | `ObjectId` | required |
| `name` | `string` | required |
| `email` | `string` | required |
| `source_refs` | `array<{system: string, id: string}>` | may be empty for employees created directly rather than synced |
| `compensation` | `{amount: Decimal128, currency: string}` | fake data only; **never** on `EmployeePublicOut`, only on `EmployeeHROut` |
| `schema_version`, `created_at`, `updated_at`, `created_by`, `updated_by` | - | standard fields |

**Why `compensation` is embedded, not referenced**: it's a 1:1,
always-read-or-never-read-together value with no independent lifecycle of
its own - referencing it would only add a join for no benefit. Field-level
exposure is controlled at the API boundary (two different out-models), not
by moving it to a separate collection.

### Indexes

| Name | Keys | Serves | Justification |
|---|---|---|---|
| `ux_employees_org_source_ref` | unique `{org_id: 1, "source_refs.system": 1, "source_refs.id": 1}`, partial filter `{"source_refs.0": {$exists: true}}` | E2 | a given source system's id must map to exactly one employee per org, so a re-run sync upserts instead of duplicating. The partial filter exists for documentation clarity: a multikey index produces no keys for an empty array, so employees with no `source_refs` never collide - the filter makes that explicit rather than relying on an implicit driver behavior |

## `assignments`

| Field | Type | Constraint |
|---|---|---|
| `_id` | `ObjectId` | |
| `org_id` | `ObjectId` | required |
| `employee_id` | `ObjectId` | required |
| `position_id` | `ObjectId` | required |
| `start_date` | `Date` | required, UTC |
| `end_date` | `Date \| null` | `null` means current |
| `fte` | `double` | `0 < fte <= 1` |
| `is_primary` | `bool` | true for an employee's primary position when they hold more than one |
| `schema_version`, `created_at`, `updated_at`, `created_by`, `updated_by` | - | standard fields |

**Why a separate collection instead of embedding on `positions` or
`employees`**: an assignment is the many-to-many join between the two, with
its own lifecycle (start/end dates) independent of either side, and the
seed story explicitly needs one employee holding two positions
concurrently - embedding on either side can't represent that cleanly.

### Indexes

| Name | Keys | Serves | Justification |
|---|---|---|---|
| `ix_assignments_org_position_start` | `{org_id: 1, position_id: 1, start_date: 1}` | A1, A2 | occupant-of-a-position lookups, current and as-of-date |
| `ix_assignments_org_employee_current` | `{org_id: 1, employee_id: 1, end_date: 1}` | A3 | an employee's current (and past) assignments, including the dual-role case |

## `sync_runs`

Created in Phase 5, alongside `services/sync.py` - a record of one
`run_sync` call, for `GET /admin/sync/runs`. No `schema_version` /
`created_by` / `updated_by` - it's an immutable log record, not an entity
that gets edited later.

| Field | Type | Constraint |
|---|---|---|
| `_id` | `ObjectId` | |
| `org_id` | `ObjectId` | required |
| `source` | `string` | which adapter produced this run (`"workday_like"`, `"bamboo_like"`) |
| `created_count`, `updated_count`, `unchanged_count`, `quarantined_count` | `int` | per-worker outcome counts for the run |
| `duration_ms` | `int` | wall-clock duration of the run |
| `started_at` | `Date` | |

### Indexes

| Name | Keys | Serves | Justification |
|---|---|---|---|
| `ix_sync_runs_org_started` | `{org_id: 1, started_at: -1}` | S2 | `GET /admin/sync/runs`, newest first |

## `quarantine`

Created in Phase 1 (part of the core data model); written to and read
starting Phase 5.

| Field | Type | Constraint |
|---|---|---|
| `_id` | `ObjectId` | |
| `org_id` | `ObjectId` | required |
| `source` | `string` | which adapter produced this (`"workday_like"`, `"bamboo_like"`) |
| `raw` | `object` | the original raw record, untouched |
| `errors` | `array<string>` | why it was quarantined |
| `created_at` | `Date` | |

### Indexes

| Name | Keys | Serves | Justification |
|---|---|---|---|
| `ix_quarantine_org_created` | `{org_id: 1, created_at: -1}` | Q2 | `GET /admin/quarantine`, newest first |

## Validators

Each collection gets a strict `$jsonSchema` validator
(`validationLevel: "strict"`, `validationAction: "error"`,
`additionalProperties: false` where practical), defined in one module per
collection under `api/app/repos/validators/` and applied via a migration
(never at request time or app startup). A test asserts each validator's
required fields and enums stay in sync with the corresponding Pydantic
canonical model, so the two can't silently drift apart.
