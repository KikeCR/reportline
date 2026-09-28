"""The org graph: the only place reporting-line edits happen.

CLAUDE.md: "Graph edits go through services/org_graph.py only (cycle check
lives there)." See docs/adr/0001-org-as-dag.md for the design rationale -
why descendants are solid-line-only via a denormalized ``solid_manager_ids``
array, why ancestors are precomputed instead, and the ``restrictSearchWithMatch``
pitfall that makes the denormalization necessary in the first place.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from bson import ObjectId
from pymongo.client_session import ClientSession

from app.db import Document
from app.errors import ConcurrentGraphEditError, CycleError, DomainValidationError, NotFoundError
from app.models.position import MAX_REPORTS_TO, Position
from app.repos import OrganizationRepo, PositionRepo, run_in_transaction

# Real organizations don't exceed this. It bounds $graphLookup's maxDepth
# and the ancestor_ids recompute loop below - see docs/data-model.md.
MAX_GRAPH_DEPTH = 20


@dataclass(frozen=True)
class GraphEdge:
    report_id: ObjectId
    manager_id: ObjectId
    relation: str
    is_primary: bool


@dataclass(frozen=True)
class Graph:
    nodes: list[Position]
    edges: list[GraphEdge]
    root_ids: list[ObjectId]


def get_descendants(org_id: ObjectId, position_id: ObjectId) -> list[Position]:
    """Solid-line subtree below ``position_id``. See ADR 0001 for why this
    is solid-only while :func:`get_ancestors` is all-edge-type.
    """
    repo = PositionRepo(org_id)
    docs = repo.get_descendants(position_id, max_depth=MAX_GRAPH_DEPTH)
    return [Position.model_validate(doc) for doc in docs]


def get_ancestors(org_id: ObjectId, position_id: ObjectId) -> list[Position]:
    repo = PositionRepo(org_id)
    docs = repo.get_ancestors(position_id)
    return [Position.model_validate(doc) for doc in docs]


def get_graph(org_id: ObjectId) -> Graph:
    """The full tenant graph as nodes + edges + root_ids - never a nested
    tree, per the brief.
    """
    repo = PositionRepo(org_id)
    docs = repo.list_for_graph()
    nodes = [Position.model_validate(doc) for doc in docs]
    edges = [
        GraphEdge(
            report_id=node.id,
            manager_id=edge.position_id,
            relation=edge.relation,
            is_primary=edge.is_primary,
        )
        for node in nodes
        for edge in node.reports_to
    ]
    root_ids = repo.root_ids()
    return Graph(nodes=nodes, edges=edges, root_ids=root_ids)


def add_reporting_line(
    org_id: ObjectId,
    manager_id: ObjectId,
    report_id: ObjectId,
    relation: str,
    is_primary: bool,
    *,
    actor_id: ObjectId | None = None,
) -> Position:
    """Add one reporting-line edge, enforcing every graph invariant inside a
    single transaction: no self-reference, no cycle across any edge type,
    at most one primary solid edge per position, and an org-wide
    ``graph_version`` check so a concurrent edit fails cleanly rather than
    silently corrupting the graph.
    """
    _validate_edge_shape(manager_id, report_id, relation, is_primary)

    def _txn(session: ClientSession) -> Position:
        position_repo = PositionRepo(org_id)
        org_repo = OrganizationRepo()
        organization = _require_organization(org_repo, org_id, session)

        manager = _require_position(position_repo, manager_id, session)
        report = _require_position(position_repo, report_id, session)

        _reject_cycle(manager, report_id)
        existing_edges = list(report.get("reports_to", []))
        _reject_duplicate_edge(existing_edges, manager_id)
        _reject_over_capacity(existing_edges)
        if is_primary:
            _reject_second_primary(existing_edges)

        new_edge = {"position_id": manager_id, "relation": relation, "is_primary": is_primary}
        updated_report = _apply_edges(
            position_repo, report, [*existing_edges, new_edge], actor_id=actor_id, session=session
        )
        _bump_graph_version_or_raise(org_repo, org_id, organization["graph_version"], session)
        return updated_report

    return run_in_transaction(_txn)


def remove_reporting_line(
    org_id: ObjectId,
    manager_id: ObjectId,
    report_id: ObjectId,
    *,
    actor_id: ObjectId | None = None,
) -> Position:
    """Remove one reporting-line edge. Removing a position's only primary
    solid edge is allowed - it leaves the position with no solid manager
    (e.g. it's being re-parented, or has become a root), which is valid.
    """

    def _txn(session: ClientSession) -> Position:
        position_repo = PositionRepo(org_id)
        org_repo = OrganizationRepo()
        organization = _require_organization(org_repo, org_id, session)
        report = _require_position(position_repo, report_id, session)

        remaining_edges = [
            edge for edge in report.get("reports_to", []) if edge["position_id"] != manager_id
        ]
        if len(remaining_edges) == len(report.get("reports_to", [])):
            raise NotFoundError("no reporting line from this manager to this position exists")

        updated_report = _apply_edges(
            position_repo, report, remaining_edges, actor_id=actor_id, session=session
        )
        _bump_graph_version_or_raise(org_repo, org_id, organization["graph_version"], session)
        return updated_report

    return run_in_transaction(_txn)


def move_subtree(
    org_id: ObjectId,
    position_id: ObjectId,
    new_manager_id: ObjectId,
    *,
    relation: str = "solid",
    is_primary: bool = True,
    actor_id: ObjectId | None = None,
) -> Position:
    """Re-parent ``position_id`` (and, implicitly, everything beneath it) by
    replacing its current primary solid edge with a new one to
    ``new_manager_id``, atomically. A position with no current primary solid
    edge simply gains one.
    """
    _validate_edge_shape(new_manager_id, position_id, relation, is_primary)

    def _txn(session: ClientSession) -> Position:
        position_repo = PositionRepo(org_id)
        org_repo = OrganizationRepo()
        organization = _require_organization(org_repo, org_id, session)

        new_manager = _require_position(position_repo, new_manager_id, session)
        report = _require_position(position_repo, position_id, session)

        _reject_cycle(new_manager, position_id)

        edges_without_old_primary = [
            edge
            for edge in report.get("reports_to", [])
            if not (edge["relation"] == "solid" and edge["is_primary"])
        ]
        _reject_duplicate_edge(edges_without_old_primary, new_manager_id)
        _reject_over_capacity(edges_without_old_primary)

        new_edge = {
            "position_id": new_manager_id,
            "relation": relation,
            "is_primary": is_primary,
        }
        updated_report = _apply_edges(
            position_repo,
            report,
            [*edges_without_old_primary, new_edge],
            actor_id=actor_id,
            session=session,
        )
        _bump_graph_version_or_raise(org_repo, org_id, organization["graph_version"], session)
        return updated_report

    return run_in_transaction(_txn)


def _validate_edge_shape(
    manager_id: ObjectId, report_id: ObjectId, relation: str, is_primary: bool
) -> None:
    if manager_id == report_id:
        raise DomainValidationError("a position cannot report to itself")
    if relation not in ("solid", "dotted"):
        raise DomainValidationError(f"unknown relation: {relation!r}")
    if relation == "dotted" and is_primary:
        raise DomainValidationError("a dotted-line edge cannot be marked primary")


def _require_organization(
    org_repo: OrganizationRepo, org_id: ObjectId, session: ClientSession
) -> Document:
    organization = org_repo.get_by_id(org_id, session=session)
    if organization is None:
        raise NotFoundError(f"organization {org_id} not found")
    return organization


def _require_position(
    position_repo: PositionRepo, position_id: ObjectId, session: ClientSession
) -> Document:
    position = position_repo.get_by_id(position_id, session=session)
    if position is None:
        raise NotFoundError(f"position {position_id} not found")
    return position


def _reject_cycle(manager: Document, report_id: ObjectId) -> None:
    """``ancestor_ids`` already unions every edge type, so one membership
    check catches a cycle whether it would close through a solid or dotted
    path, direct or indirect.
    """
    if report_id in manager.get("ancestor_ids", []):
        raise CycleError("this reporting line would create a cycle")


def _reject_duplicate_edge(existing_edges: list[Document], manager_id: ObjectId) -> None:
    if any(edge["position_id"] == manager_id for edge in existing_edges):
        raise DomainValidationError("this reporting line already exists")


def _reject_over_capacity(existing_edges: list[Document]) -> None:
    if len(existing_edges) >= MAX_REPORTS_TO:
        raise DomainValidationError(f"a position may have at most {MAX_REPORTS_TO} reporting lines")


def _reject_second_primary(existing_edges: list[Document]) -> None:
    has_primary_solid = any(
        edge["relation"] == "solid" and edge["is_primary"] for edge in existing_edges
    )
    if has_primary_solid:
        raise DomainValidationError(
            "position already has a primary solid reporting line; remove it first"
        )


def _apply_edges(
    position_repo: PositionRepo,
    report: Document,
    new_reports_to: list[Document],
    *,
    actor_id: ObjectId | None,
    session: ClientSession,
) -> Position:
    new_solid_manager_ids = [
        edge["position_id"] for edge in new_reports_to if edge["relation"] == "solid"
    ]
    now = datetime.now(UTC)

    position_repo.update_edges_and_ancestors(
        report["_id"],
        reports_to=new_reports_to,
        solid_manager_ids=new_solid_manager_ids,
        ancestor_ids=report.get("ancestor_ids", []),
        updated_at=now,
        updated_by=actor_id,
        session=session,
    )
    _recompute_ancestor_ids_for_subtree(
        position_repo, report["_id"], updated_at=now, session=session
    )

    updated = position_repo.get_by_id(report["_id"], session=session)
    assert updated is not None  # noqa: S101 - just written inside this same transaction
    return Position.model_validate(updated)


def _recompute_ancestor_ids_for_subtree(
    position_repo: PositionRepo,
    changed_position_id: ObjectId,
    *,
    updated_at: datetime,
    session: ClientSession,
) -> None:
    """Recompute ``ancestor_ids`` for ``changed_position_id`` and every
    position that (directly or indirectly, via any edge type) reports to it.

    A position's ancestor set is always the union of ``{manager_id} |
    manager.ancestor_ids`` over every one of its reports_to edges. Since a
    position's managers can themselves be outside the affected set (already
    stable), this iterates to a fixed point rather than assuming a single
    top-down pass suffices - correct for any DAG, and bounded by
    MAX_GRAPH_DEPTH since that's the deepest a chain can be.
    """
    affected_ids = {changed_position_id} | {
        doc["_id"] for doc in position_repo.in_subtree_of(changed_position_id, session=session)
    }
    by_id = {
        doc["_id"]: doc for doc in position_repo.get_many_by_ids(affected_ids, session=session)
    }

    external_manager_ids = {
        edge["position_id"]
        for doc in by_id.values()
        for edge in doc["reports_to"]
        if edge["position_id"] not in by_id
    }
    external_ancestors = {
        doc["_id"]: set(doc["ancestor_ids"])
        for doc in position_repo.get_many_by_ids(external_manager_ids, session=session)
    }

    for _ in range(MAX_GRAPH_DEPTH + 1):
        changed = False
        for doc in by_id.values():
            new_ancestors: set[ObjectId] = set()
            for edge in doc["reports_to"]:
                manager_id = edge["position_id"]
                new_ancestors.add(manager_id)
                if manager_id in by_id:
                    new_ancestors.update(by_id[manager_id]["ancestor_ids"])
                else:
                    new_ancestors.update(external_ancestors.get(manager_id, set()))
            if set(doc["ancestor_ids"]) != new_ancestors:
                doc["ancestor_ids"] = list(new_ancestors)
                changed = True
        if not changed:
            break

    updates = {pid: doc["ancestor_ids"] for pid, doc in by_id.items()}
    position_repo.bulk_update_ancestor_ids(updates, updated_at=updated_at, session=session)


def _bump_graph_version_or_raise(
    org_repo: OrganizationRepo, org_id: ObjectId, expected_version: int, session: ClientSession
) -> None:
    if not org_repo.bump_graph_version(org_id, expected_version, session=session):
        raise ConcurrentGraphEditError(
            "the org graph changed while this edit was in progress; retry"
        )
