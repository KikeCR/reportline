# 0001 - Modeling the org as a DAG

## Status

Accepted

## Context

An organization's reporting structure isn't a tree: a position can have a
solid-line manager and one or more dotted-line managers at the same time,
and (per the seed story) two positions can even be solid-line co-managed.
That makes it a directed acyclic graph, not a tree, and MongoDB's graph
tooling ($graphLookup) has a specific pitfall that shapes how the schema
has to be built to use it correctly.

## Decision

### Position vs. employee vs. assignment

Three separate collections, not one:

- **`positions`** is the graph. It has no idea who (if anyone) occupies it.
- **`employees`** is a person, with no idea what position(s) they hold.
- **`assignments`** is the many-to-many join between the two, with its own
  lifecycle (`start_date`/`end_date`, `fte`, `is_primary`).

This is what makes the seed story representable at all: a vacant position
(a `positions` doc with no current `assignments`), and one person holding
two part-time positions concurrently (one `employees` doc, two concurrent
`assignments` docs). Embedding occupancy on either side can't express
either case cleanly.

### Edges embedded on `positions`, not a separate `edges` collection

`reports_to` lives on the position document itself, not as rows in a
separate collection. A position's edges are small (capped at 8, see below),
bounded, and are always read together with the position - there's no access
pattern that needs an edge without its position or vice versa. A separate
`edges` collection would add a join for zero benefit here.

### The `restrictSearchWithMatch` pitfall, and why `solid_manager_ids` exists

The obvious way to compute descendants would be a single `$graphLookup`
starting from `reports_to`, scoped with `restrictSearchWithMatch: {org_id}`,
filtered somehow to solid edges only. That doesn't work:
**`restrictSearchWithMatch` filters whole documents, not elements of an
array field.** There's no way to tell `$graphLookup` "only follow the
`reports_to` entries where `relation == "solid"`" - it can only say "only
consider documents matching this predicate," and every position document in
an org matches `{org_id: ...}` regardless of which of its edges are solid.

The fix is denormalization: `solid_manager_ids` is a plain array of
`ObjectId`s, containing exactly the `position_id`s from `reports_to` where
`relation == "solid"` (enforced by a model validator - see
`app/models/position.py`). `$graphLookup`'s `connectToField` then targets
this array directly, so "only follow solid edges" is true by construction,
not by post-filtering. This is also why `get_descendants` is
solid-line-only by design (per the brief) - dotted lines are informational
overlays, not part of the management hierarchy a subtree query should
follow.

### Why `ancestor_ids` is precomputed instead of a second `$graphLookup`

Unlike descendants, **`ancestor_ids` unions every edge type** (solid and
dotted). Two reasons it's precomputed on write rather than queried live:

1. It's the query behind `manager`-role permission scoping (P6 in
   docs/access-patterns.md), which runs on nearly every request a manager
   makes. A live `$graphLookup` on every read would put graph traversal on
   the hot path of authorization; a precomputed, indexed array field turns
   it into one indexed equality query.
2. All-edge-type traversal can't reuse the `solid_manager_ids` trick above
   in the other direction as cleanly, since an ancestor set is a union
   across the *two* denormalized concerns (which edges are solid, which are
   dotted) rather than a single connect field.

The trade-off is real, and it's the reason graph edits are more expensive
than a naive edge write: adding or removing a reporting line must recompute
`ancestor_ids` for every position affected, not just the two endpoints (see
"Ancestor recomputation" below). Reads are cheap; writes pay for it. Given
this is an org chart - read far more often than written - that's the right
trade-off.

### Why `reports_to` (and `solid_manager_ids`) are capped at 8, not unbounded

The MongoDB standards this project follows forbid unbounded arrays. 8 gives
real headroom over the seed data's most extreme case (two solid co-managers
plus a dotted line) without being unbounded. The cap is enforced twice: in
the Pydantic model (`Field(max_length=8)`) for anything constructed
in-process, and in the `$jsonSchema` validator (`maxItems: 8`) so it holds
even against a write that bypasses the model - e.g. a future direct
migration or admin script.

`ancestor_ids` is *not* capped the same way, because it grows with
organizational **depth**, not a position's own fan-out. Depth is bounded
instead, by `MAX_GRAPH_DEPTH = 20` in `services/org_graph.py`, used as
`$graphLookup`'s `maxDepth` and as the iteration limit for ancestor
recomputation (see below).

### Addition beyond the brief's collection list: `organizations`

Covered in full in `docs/data-model.md`. In short: `add_reporting_line`
needs an "org-level `graph_version`" field per the brief, and there's no
natural place for an org-level field to live without an org-level document.
`organizations._id` *is* the org id used everywhere else, so
`OrganizationRepo` isn't a `ScopedRepo` subclass - there's no separate
tenant field to scope by.

### `graph_version` and `with_transaction`'s automatic retry, together

The brief asks for both: an org-level `graph_version` for optimistic
concurrency, *and* using `with_transaction`'s automatic retry of transient
transaction errors. These aren't redundant - they cover different failure
modes:

- Every graph mutation writes to the *same* `organizations` document (to
  bump `graph_version`). When two graph edits run concurrently, MongoDB's
  storage engine detects the write-write conflict on that shared document
  and raises a `TransientTransactionError`-labeled error immediately -
  `with_transaction` catches this and silently retries the *entire*
  callback with a fresh snapshot. This handles the common case
  transparently: by the time a retried attempt's conditional
  `graph_version` update runs, it's working from fresh data and normally
  just succeeds.
- The explicit `graph_version` check (`OrganizationRepo.bump_graph_version`
  returning `False` -> `ConcurrentGraphEditError`) is the defense-in-depth
  fallback for any case that isn't a same-document write conflict, and it's
  what makes the invariant explicit, typed, and directly testable rather
  than an implicit property of driver retry behavior.

`tests/services/test_org_graph.py::test_concurrent_opposite_edits_cannot_create_a_cycle`
exercises this for real: two threads concurrently try to add opposite
edges between the same two positions (which, if both succeeded, would form
a 2-cycle) against a real replica set. Exactly one succeeds; the other is
rejected with either `CycleError` (it retried and then saw the cycle) or
`ConcurrentGraphEditError` (the version check caught it) - the test doesn't
assume which, only that the invariant holds either way.

### Ancestor recomputation is a fixed-point pass, not one top-down sweep

When a position's manager set changes, every position that (directly or
indirectly, via any edge type) reports to it may need its `ancestor_ids`
recomputed - not just its immediate reports. The affected set is found
cheaply: it's exactly `{changed_position} ∪ in_subtree_of(changed_position)`,
using the very index (`ix_positions_org_ancestor_ids`) that this same
recomputation keeps correct. Within that set,
`_recompute_ancestor_ids_for_subtree` (in `services/org_graph.py`)
iterates - each position's ancestor set is `{manager_id} ∪
manager.ancestor_ids` unioned over every edge - until nothing changes,
capped at `MAX_GRAPH_DEPTH` passes. A single top-down pass isn't always
correct here because a position deep in the affected set can have its own
independent manager outside the changed subtree (e.g. an unrelated dotted
line), and getting a correct topological order cheaply isn't worth the
complexity at this scale (~120 positions at seed scale); the fixed-point
loop is simple, provably terminates, and is proven correct by
`test_add_reporting_line_propagates_ancestor_ids_down_the_subtree`.

### `move_subtree` semantics

`move_subtree(org_id, position_id, new_manager_id)` re-parents a position by
replacing its current *primary solid* edge (if any) with a new solid,
primary edge to `new_manager_id`, in one transaction with one
`graph_version` bump - not a `remove_reporting_line` call followed by a
separate `add_reporting_line` call, which would take two version bumps and
leave a window where the position has no manager at all if the process
crashed between them.

### `ClientSession` as the one narrow exception to "only repos/ touches pymongo"

`services/org_graph.py` imports `pymongo.client_session.ClientSession` for
type hints, and calls `app.repos.transaction.run_in_transaction`, which
hands the service a live session to pass into repo calls. The service never
calls a collection method on that session directly - it's an opaque handle
threaded through repo methods so several of them can commit or abort
together. This is a deliberate, narrow exception to CLAUDE.md's "only
repos/ touches pymongo collections" rule, not a loophole: nothing in
`services/` ever does `session.client...` or touches a `Collection`.

### Test database: `MongoDBAtlasLocalContainer`, not a hand-rolled replica set

`tests/conftest.py` uses `testcontainers`'s `MongoDBAtlasLocalContainer`
rather than scripting `mongod --replSet rs0` + `rs.initiate()` by hand. That
image runs as a single-node replica set out of the box - exactly what
`$graphLookup` and transactions need - without test setup code that talks
to `rs.initiate()` itself. This is deliberately different from
docker-compose's local-dev Mongo, which *does* hand-roll `rs0` + keyfile
auth + least-privilege users, because local dev is meant to demonstrate the
production security model; the test suite only needs transactions to work
reliably and fast, so it takes the simpler path.

## Consequences

- Every graph mutation is more expensive than a single-document write
  (it recomputes ancestor_ids for a subtree, not just one document), which
  is the accepted cost of making the hot-path permission query
  (`in_subtree_of`) a single indexed read.
- The `organizations` collection is now a soft dependency of every graph
  mutation (it must exist before `add_reporting_line`/`remove_reporting_line`/
  `move_subtree` can run) - `seed.py` creates it first, before any position.
- `MAX_REPORTS_TO` (8) and `MAX_GRAPH_DEPTH` (20) are the two hard ceilings
  a real deployment would need to revisit if an org ever legitimately
  exceeded them; both are named constants in one place each
  (`app/models/position.py`, `app/services/org_graph.py`) rather than
  scattered magic numbers.
