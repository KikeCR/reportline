from concurrent.futures import ThreadPoolExecutor

import pytest
from bson import ObjectId

from app.errors import ConcurrentGraphEditError, CycleError, DomainValidationError, NotFoundError
from app.services import org_graph
from tests.factories import build_organization, build_position

pytestmark = pytest.mark.integration


def _seed_org(db) -> ObjectId:
    organization = build_organization()
    db["organizations"].insert_one(organization)
    return organization["_id"]


def _seed_position(db, org_id: ObjectId, **overrides) -> ObjectId:
    position = build_position(org_id, **overrides)
    db["positions"].insert_one(position)
    return position["_id"]


def test_add_reporting_line_rejects_self_reference(db):
    org_id = _seed_org(db)
    position_id = _seed_position(db, org_id)

    with pytest.raises(DomainValidationError, match="cannot report to itself"):
        org_graph.add_reporting_line(org_id, position_id, position_id, "solid", True)


def test_add_reporting_line_rejects_unknown_position(db):
    org_id = _seed_org(db)
    position_id = _seed_position(db, org_id)

    with pytest.raises(NotFoundError):
        org_graph.add_reporting_line(org_id, ObjectId(), position_id, "solid", True)


def test_add_reporting_line_rejects_direct_cycle(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    with pytest.raises(CycleError):
        org_graph.add_reporting_line(org_id, vp, ceo, "dotted", False)


def test_add_reporting_line_rejects_indirect_cycle(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")
    director = _seed_position(db, org_id, title="Director")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)
    org_graph.add_reporting_line(org_id, vp, director, "solid", True)

    with pytest.raises(CycleError):
        org_graph.add_reporting_line(org_id, director, ceo, "dotted", False)


def test_add_reporting_line_rejects_a_second_primary_solid_edge(db):
    org_id = _seed_org(db)
    vp1 = _seed_position(db, org_id, title="VP1")
    vp2 = _seed_position(db, org_id, title="VP2")
    shared = _seed_position(db, org_id, title="Shared")
    org_graph.add_reporting_line(org_id, vp1, shared, "solid", True)

    with pytest.raises(DomainValidationError, match="already has a primary solid"):
        org_graph.add_reporting_line(org_id, vp2, shared, "solid", True)


def test_add_reporting_line_allows_dual_solid_co_managers_with_one_primary(db):
    org_id = _seed_org(db)
    vp1 = _seed_position(db, org_id, title="VP1")
    vp2 = _seed_position(db, org_id, title="VP2")
    shared = _seed_position(db, org_id, title="Shared")
    org_graph.add_reporting_line(org_id, vp1, shared, "solid", True)

    updated = org_graph.add_reporting_line(org_id, vp2, shared, "solid", False)

    assert set(updated.solid_manager_ids) == {vp1, vp2}
    primaries = [e for e in updated.reports_to if e.is_primary]
    assert len(primaries) == 1
    assert primaries[0].position_id == vp1

    # Both co-managers must see it as a solid-line descendant.
    assert {p.id for p in org_graph.get_descendants(org_id, vp1)} == {shared}
    assert {p.id for p in org_graph.get_descendants(org_id, vp2)} == {shared}


def test_add_reporting_line_rejects_unknown_relation(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")

    with pytest.raises(DomainValidationError, match="unknown relation"):
        org_graph.add_reporting_line(org_id, ceo, vp, "loose", False)


def test_add_reporting_line_rejects_dotted_edge_marked_primary(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")

    with pytest.raises(DomainValidationError, match="dotted-line edge cannot be marked primary"):
        org_graph.add_reporting_line(org_id, ceo, vp, "dotted", True)


def test_add_reporting_line_rejects_duplicate_edge(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    with pytest.raises(DomainValidationError, match="already exists"):
        org_graph.add_reporting_line(org_id, ceo, vp, "dotted", False)


def test_add_reporting_line_rejects_over_capacity(db):
    org_id = _seed_org(db)
    report = _seed_position(db, org_id, title="Report")
    for _ in range(8):
        manager = _seed_position(db, org_id)
        org_graph.add_reporting_line(org_id, manager, report, "dotted", False)

    ninth_manager = _seed_position(db, org_id)
    with pytest.raises(DomainValidationError, match="at most 8"):
        org_graph.add_reporting_line(org_id, ninth_manager, report, "dotted", False)


def test_add_reporting_line_propagates_ancestor_ids_down_the_subtree(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")
    director = _seed_position(db, org_id, title="Director")
    org_graph.add_reporting_line(org_id, vp, director, "solid", True)

    # Director already reports to VP; now VP starts reporting to CEO - the
    # brief requires the whole affected subtree's ancestor_ids to update,
    # not just VP's.
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    director_ancestors = {p.id for p in org_graph.get_ancestors(org_id, director)}
    assert director_ancestors == {vp, ceo}


def test_remove_reporting_line_leaves_no_primary_and_updates_descendants(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")
    director = _seed_position(db, org_id, title="Director")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)
    org_graph.add_reporting_line(org_id, vp, director, "solid", True)

    org_graph.remove_reporting_line(org_id, ceo, vp)

    updated_vp = org_graph.get_ancestors(org_id, vp)
    assert updated_vp == []
    director_ancestors = {p.id for p in org_graph.get_ancestors(org_id, director)}
    assert director_ancestors == {vp}


def test_remove_reporting_line_raises_not_found_when_no_such_edge(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")

    with pytest.raises(NotFoundError):
        org_graph.remove_reporting_line(org_id, ceo, vp)


def test_move_subtree_reparents_and_rejects_a_cycle(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp1 = _seed_position(db, org_id, title="VP1")
    vp2 = _seed_position(db, org_id, title="VP2")
    director = _seed_position(db, org_id, title="Director")
    org_graph.add_reporting_line(org_id, ceo, vp1, "solid", True)
    org_graph.add_reporting_line(org_id, ceo, vp2, "solid", True)
    org_graph.add_reporting_line(org_id, vp1, director, "solid", True)

    org_graph.move_subtree(org_id, director, vp2)

    ancestors = {p.id for p in org_graph.get_ancestors(org_id, director)}
    assert ancestors == {vp2, ceo}

    with pytest.raises(CycleError):
        org_graph.move_subtree(org_id, vp2, director)


def test_get_graph_returns_nodes_edges_and_root_ids(db):
    org_id = _seed_org(db)
    ceo = _seed_position(db, org_id, title="CEO")
    vp = _seed_position(db, org_id, title="VP")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    graph = org_graph.get_graph(org_id)

    assert {n.id for n in graph.nodes} == {ceo, vp}
    assert graph.root_ids == [ceo]
    assert len(graph.edges) == 1
    assert graph.edges[0].report_id == vp
    assert graph.edges[0].manager_id == ceo


def test_concurrent_opposite_edits_cannot_create_a_cycle(db):
    org_id = _seed_org(db)
    position_a = _seed_position(db, org_id, title="A")
    position_b = _seed_position(db, org_id, title="B")

    def add_a_reports_to_b():
        return org_graph.add_reporting_line(org_id, position_b, position_a, "dotted", False)

    def add_b_reports_to_a():
        return org_graph.add_reporting_line(org_id, position_a, position_b, "dotted", False)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_1 = executor.submit(add_a_reports_to_b)
        future_2 = executor.submit(add_b_reports_to_a)

        results = []
        for future in (future_1, future_2):
            try:
                results.append(("ok", future.result()))
            except (CycleError, ConcurrentGraphEditError) as exc:
                results.append(("rejected", exc))

    outcomes = [kind for kind, _ in results]
    assert outcomes.count("ok") == 1
    assert outcomes.count("rejected") == 1

    # Whichever edit won, the final graph must have no cycle: A and B
    # cannot both be in each other's ancestor_ids.
    a_ancestors = {p.id for p in org_graph.get_ancestors(org_id, position_a)}
    b_ancestors = {p.id for p in org_graph.get_ancestors(org_id, position_b)}
    assert not (position_b in a_ancestors and position_a in b_ancestors)
