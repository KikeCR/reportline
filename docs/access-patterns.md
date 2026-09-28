# Access patterns

Every query the app runs, written before any collection or index is
designed. Indexes in `docs/data-model.md` and `api/migrations/` are derived
from this list - a new query pattern should be added here first, then given
an index, then implemented.

Cardinality assumes the seeded demo scale (Tenant A: ~120 positions,
Tenant B: smaller) but is written for what a real tenant could plausibly
reach (a few thousand positions, tens of thousands of employees across all
tenants).

## positions

| # | Query | Filter | Sort | Projection | Cardinality | Used by |
|---|---|---|---|---|---|---|
| P1 | Get one position | `{_id, org_id}` | - | full doc | 1 | `GET /org/positions/{id}`, internal lookups before any graph mutation |
| P2 | Descendants of a position | `$graphLookup` over `solid_manager_ids`, `restrictSearchWithMatch: {org_id}`, `startWith: position_id`, `maxDepth` bounded (org depth is capped), `depthField: "depth"` | - | `{_id, title, department, status, depth}` | up to full subtree (~120 at seed scale) | `GET /org/positions/{id}/descendants`, `org_graph.get_descendants`, manager-scope permission checks |
| P3 | Ancestors of a position | `{org_id, _id: {$in: ancestor_ids}}` (read `ancestor_ids` off the position first, then one `$in` fetch - no second `$graphLookup` needed because `ancestor_ids` is precomputed) | - | `{_id, title, department}` | chain depth (4-5 at seed scale) | `org_graph.get_ancestors`, breadcrumb / detail drawer |
| P4 | Direct reports across all edge types | `{org_id, "reports_to.position_id": position_id}` | `title` | `{_id, title, reports_to}` | small (single-digit fan-out) | `org_graph` edge validation before add/remove, node detail drawer's "direct reports" count |
| P5 | Solid-line direct reports only | `{org_id, solid_manager_ids: position_id}` | - | `{_id}` | small | same as P4, solid-only variant used as the `$graphLookup` traversal edge itself |
| P6 | Positions in a manager's subtree (permission scope) | `{org_id, ancestor_ids: position_id}` | - | role-dependent out-model fields only | subtree size | `services/permissions.py` - the single indexed query a `manager` role's every list/read is filtered through |
| P7 | Full graph for a tenant | `{org_id, status: {$ne: "closed"}}` | - | `{_id, title, department, status, reports_to, solid_manager_ids}` | full tenant (~120 at seed scale) | `GET /org/graph`, `org_graph.get_graph` (returns nodes+edges+root_ids, never a nested tree) |
| P8 | Root positions of a tenant | `{org_id, reports_to: {$size: 0}}` | - | `{_id}` | tiny (1-2) | `org_graph.get_graph`'s `root_ids` |
| P9 | Subtree fetch for `ancestor_ids` recompute | `{org_id, _id: {$in: subtree_position_ids}}` | - | `{_id, ancestor_ids, reports_to}` | affected subtree only | `org_graph.add_reporting_line` / `move_subtree`, inside the mutation transaction |
| P10 | Optimistic concurrency check + update | `findOneAndUpdate({_id, org_id, graph_version: expected_version}, {$set: ..., $inc: {graph_version: 1}})` | - | - | 1 | every graph mutation - a mismatch means a concurrent edit happened; the caller retries or fails cleanly |
| P11 | Dedup by source system + id | `{org_id, source_refs: {$elemMatch: {system, id}}}` - same `$elemMatch` requirement as E2, for the same reason | - | full doc | 0 or 1 (enforced unique) | `services/sync.py` upsert path (Phase 5), added by migration 0006 alongside `positions.source_refs` |

## employees

| # | Query | Filter | Sort | Projection | Cardinality | Used by |
|---|---|---|---|---|---|---|
| E1 | Get one employee | `{_id, org_id}` | - | role-dependent (`EmployeePublicOut` vs `EmployeeHROut`) | 1 | `GET /employees/{id}` |
| E2 | Dedup by source system + id | `{org_id, source_refs: {$elemMatch: {system, id}}}` - **must** use `$elemMatch`, not two separate dotted-path conditions, or an employee with refs in two different systems could false-match a query for a third combination | - | `{_id}` | 0 or 1 (enforced unique) | `services/sync.py` upsert path (Phase 5) - defined now because the collection and its unique index are created in Phase 1 |
| E3 | Employees by name (admin search, future) | `{org_id, name: {$regex: ...}}` | `name` | `{_id, name}` | small result set | noted for completeness; not exposed as an endpoint in Phase 1-2, no dedicated index added until it is |

## assignments

| # | Query | Filter | Sort | Projection | Cardinality | Used by |
|---|---|---|---|---|---|---|
| A1 | Current occupant(s) of a position | `{org_id, position_id, end_date: null}` | - | `{employee_id, fte, is_primary}` | usually 1, up to 2 for shared/part-time roles | node detail drawer; `services/sync.py`'s per-worker pass 1 |
| A1b | Current occupant(s) of many positions in one query | `{org_id, position_id: {$in: [...]}, end_date: null}` | - | `{employee_id, fte, is_primary, position_id}` | one row per occupied position | "people" view of the graph (`get_graph`) - batched so the whole-graph read stays at a small constant number of queries (ADR 0002), not one query per position |
| A2 | Occupant(s) as of a date | `{org_id, position_id, start_date: {$lte: as_of}, $or: [{end_date: null}, {end_date: {$gte: as_of}}]}` | - | `{employee_id, fte, is_primary}` | usually 1-2 | single-position as-of lookups (none currently exposed as an endpoint) |
| A2b | Batched form of A2 | same as A2 with `position_id: {$in: [...]}` | - | same as A1b | one row per occupied position as of that date | `GET /org/graph?as_of=...` |
| A3 | Current assignments for an employee | `{org_id, employee_id, end_date: null}` | - | `{position_id, fte, is_primary}` | usually 1, up to 2 (dual-role case) | employee detail, "which position(s) does this person hold" |
| A4 | Insert / end-date an assignment | point insert / `findOneAndUpdate` by `{_id, org_id}` | - | - | 1 | position moves, terminations, sync writes |

## sync_runs

| # | Query | Filter | Sort | Projection | Cardinality | Used by |
|---|---|---|---|---|---|---|
| S1 | Insert a run record | point insert | - | - | 1 | `services/sync.py`, once per `run_sync` call |
| S2 | List runs for a tenant | `{org_id}` | `started_at desc` | full doc | small-to-moderate | `GET /admin/sync/runs` |

## quarantine

Collection is created in Phase 1 (it's part of the core data model) but only
written to and read starting Phase 5, once `services/sync.py` exists.

| # | Query | Filter | Sort | Projection | Cardinality | Used by |
|---|---|---|---|---|---|---|
| Q1 | Insert a quarantined record | point insert | - | - | 1 | `services/sync.py` on any unresolved/invalid source record |
| Q2 | List quarantine for a tenant | `{org_id}` | `created_at desc` | full doc | small-to-moderate | `GET /admin/quarantine` |

## Notes that shaped the schema

- **`solid_manager_ids` exists purely so P2/P5 can be a single, cheap
  `$graphLookup`.** `$graphLookup`'s `restrictSearchWithMatch` filters
  *documents*, not array elements - it cannot express "follow only the solid
  edge inside this array of mixed solid/dotted edges." Denormalizing the
  solid-only manager set into its own array turns the traversal into a plain
  field-to-field graph lookup. See ADR 0001 for the full pitfall writeup.
- **`ancestor_ids` exists so P3 and P6 are a single indexed query each**,
  not a `$graphLookup` on every read. Ancestors change only when the graph
  is edited, so it's cheap to keep denormalized and expensive to recompute
  on every permission check otherwise - `manager` role scoping (P6) is on
  the hot path of nearly every request that role makes.
- **No query ever omits `org_id`.** Every pattern above starts with it; this
  is what `ScopedRepo` enforces structurally rather than by convention.
- **No `skip()`-based pagination appears anywhere above.** At seed scale
  full-collection reads are fine; the one place this would matter later
  (`E3`-style search, `GET /admin/quarantine` at real scale) is noted to use
  cursor-based pagination by `_id` if/when it's built, never `skip()`.
