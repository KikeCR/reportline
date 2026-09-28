from datetime import UTC, datetime
from decimal import Decimal

import pytest
from bson import ObjectId

from app.repos import AssignmentRepo, EmployeeRepo, PositionRepo
from app.services import org_graph
from tests.factories import build_organization

pytestmark = pytest.mark.integration


def _seed_org(db) -> ObjectId:
    organization = build_organization()
    db["organizations"].insert_one(organization)
    return organization["_id"]


def test_get_graph_positions_view_returns_nodes_edges_and_roots(client, db):
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create("CEO", "Executive")
    vp = PositionRepo(org_id).create("VP", "Engineering")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    response = client.get("/api/v1/org/graph", headers={"X-Org-Id": str(org_id)})

    assert response.status_code == 200
    body = response.json
    assert {n["id"] for n in body["nodes"]} == {str(ceo), str(vp)}
    assert body["root_ids"] == [str(ceo)]
    assert body["edges"] == [
        {"report_id": str(vp), "manager_id": str(ceo), "relation": "solid", "is_primary": True}
    ]
    assert all(n["occupants"] is None for n in body["nodes"])


def test_get_graph_people_view_attaches_occupant_names(client, db):
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create("CEO", "Executive")
    employee_id = EmployeeRepo(org_id).create(
        "Ada Lovelace", "ada@example.com", compensation_amount=Decimal("100000")
    )
    AssignmentRepo(org_id).create(employee_id, ceo, start_date=datetime.now(UTC))

    response = client.get(
        "/api/v1/org/graph", query_string={"view": "people"}, headers={"X-Org-Id": str(org_id)}
    )

    assert response.status_code == 200
    node = next(n for n in response.json["nodes"] if n["id"] == str(ceo))
    assert node["occupants"] == [
        {"employee_id": str(employee_id), "name": "Ada Lovelace", "fte": 1.0, "is_primary": True}
    ]


def test_get_graph_422s_for_an_unknown_view(client, db):
    org_id = _seed_org(db)

    response = client.get(
        "/api/v1/org/graph", query_string={"view": "bogus"}, headers={"X-Org-Id": str(org_id)}
    )

    assert response.status_code == 422
