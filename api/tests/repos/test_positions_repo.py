import pytest
from bson import ObjectId

from app.repos import PositionRepo
from tests.factories import build_graph_from_spec, build_position

pytestmark = pytest.mark.integration


def _insert_all(db, positions: dict[str, dict]) -> None:
    db["positions"].insert_many(list(positions.values()))


def test_create_inserts_an_edgeless_active_position_scoped_to_the_org(db):
    org_id = ObjectId()
    repo = PositionRepo(org_id)

    position_id = repo.create("VP Engineering", "Engineering")

    doc = repo.get_by_id(position_id)
    assert doc is not None
    assert doc["org_id"] == org_id
    assert doc["status"] == "active"
    assert doc["reports_to"] == []


def test_delete_all_only_removes_this_tenants_documents(db):
    org_a, org_b = ObjectId(), ObjectId()
    PositionRepo(org_a).create("A", "Eng")
    PositionRepo(org_b).create("B", "Eng")

    deleted = PositionRepo(org_a).delete_all()

    assert deleted == 1
    assert db["positions"].count_documents({"org_id": org_b}) == 1
    assert db["positions"].count_documents({"org_id": org_a}) == 0


def test_tenant_isolation_on_get_by_id(db):
    org_a, org_b = ObjectId(), ObjectId()
    position_in_b = build_position(org_b)
    db["positions"].insert_one(position_in_b)

    repo_a = PositionRepo(org_a)

    assert repo_a.get_by_id(position_in_b["_id"]) is None


def test_tenant_isolation_on_in_subtree_of(db):
    org_a, org_b = ObjectId(), ObjectId()
    manager_id = ObjectId()
    leaked_position = build_position(org_b, ancestor_ids=[manager_id])
    db["positions"].insert_one(leaked_position)

    repo_a = PositionRepo(org_a)

    assert repo_a.in_subtree_of(manager_id) == []


def test_get_descendants_follows_solid_line_only(db):
    org_id = ObjectId()
    positions = build_graph_from_spec(org_id, "CEO>VP1, CEO>VP2, VP1>Dir1, Dir1..VP2")
    _insert_all(db, positions)
    repo = PositionRepo(org_id)

    descendants = repo.get_descendants(positions["CEO"]["_id"], max_depth=20)

    titles = {d["title"] for d in descendants}
    assert titles == {"VP1", "VP2", "Dir1"}


def test_get_descendants_excludes_dotted_only_reports(db):
    org_id = ObjectId()
    # Dir1 has a dotted line to VP2 but VP2's solid manager is CEO, not Dir1 -
    # Dir1's descendants must not include VP2.
    positions = build_graph_from_spec(org_id, "CEO>VP1, CEO>VP2, VP1>Dir1, Dir1..VP2")
    _insert_all(db, positions)
    repo = PositionRepo(org_id)

    descendants = repo.get_descendants(positions["Dir1"]["_id"], max_depth=20)

    assert descendants == []


def test_get_descendants_handles_dual_solid_co_managers(db):
    org_id = ObjectId()
    positions = build_graph_from_spec(org_id, "CEO>VP1, VP1>Shared, VP2>Shared, CEO>VP2")
    _insert_all(db, positions)
    repo = PositionRepo(org_id)

    # Both VP1 and VP2 solid-report Shared as a co-managed position; it must
    # show up as a descendant of both.
    assert {d["title"] for d in repo.get_descendants(positions["VP1"]["_id"], max_depth=20)} == {
        "Shared"
    }
    assert {d["title"] for d in repo.get_descendants(positions["VP2"]["_id"], max_depth=20)} == {
        "Shared"
    }


def test_get_ancestors_includes_dotted_line_ancestors(db):
    org_id = ObjectId()
    positions = build_graph_from_spec(org_id, "CEO>VP1, CEO>VP2, VP1>Dir1, Dir1..VP2")
    _insert_all(db, positions)
    repo = PositionRepo(org_id)

    ancestors = repo.get_ancestors(positions["VP2"]["_id"])

    # VP2 solid-reports to CEO AND dotted-reports to Dir1 (whose ancestors
    # are VP1, CEO) - ancestor_ids is the union across all edge types.
    assert {a["title"] for a in ancestors} == {"CEO", "VP1", "Dir1"}


def test_in_subtree_of_is_the_manager_permission_scope_query(db):
    org_id = ObjectId()
    positions = build_graph_from_spec(org_id, "CEO>VP1, VP1>Dir1, Dir1>Mgr1")
    _insert_all(db, positions)
    repo = PositionRepo(org_id)

    subtree = repo.in_subtree_of(positions["VP1"]["_id"])

    assert {p["title"] for p in subtree} == {"Dir1", "Mgr1"}


def test_direct_reports_returns_both_edge_types_sorted_by_title(db):
    org_id = ObjectId()
    positions = build_graph_from_spec(org_id, "CEO>Bravo, CEO>Alpha, Alpha..Charlie")
    _insert_all(db, positions)
    repo = PositionRepo(org_id)

    reports = repo.direct_reports(positions["CEO"]["_id"])

    assert [r["title"] for r in reports] == ["Alpha", "Bravo"]


def test_root_ids_returns_positions_with_no_reports_to(db):
    org_id = ObjectId()
    positions = build_graph_from_spec(org_id, "CEO>VP1, CEO>VP2")
    _insert_all(db, positions)
    repo = PositionRepo(org_id)

    assert repo.root_ids() == [positions["CEO"]["_id"]]
