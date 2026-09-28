import pytest
from bson import ObjectId

from app.repos import PositionRepo
from app.services import org_graph
from tests.factories import build_organization

pytestmark = pytest.mark.integration


def _seed_org(db) -> ObjectId:
    organization = build_organization()
    db["organizations"].insert_one(organization)
    return organization["_id"]


def test_post_reporting_lines_adds_an_edge(client, db):
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create("CEO", "Executive")
    vp = PositionRepo(org_id).create("VP", "Engineering")

    response = client.post(
        "/api/v1/org/reporting-lines",
        headers={"X-Org-Id": str(org_id)},
        json={
            "manager_id": str(ceo),
            "report_id": str(vp),
            "relation": "solid",
            "is_primary": True,
        },
    )

    assert response.status_code == 200
    assert response.json["reports_to"] == [
        {"position_id": str(ceo), "relation": "solid", "is_primary": True}
    ]


def test_post_reporting_lines_409s_on_a_cycle(client, db):
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create("CEO", "Executive")
    vp = PositionRepo(org_id).create("VP", "Engineering")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    response = client.post(
        "/api/v1/org/reporting-lines",
        headers={"X-Org-Id": str(org_id)},
        json={
            "manager_id": str(vp),
            "report_id": str(ceo),
            "relation": "dotted",
            "is_primary": False,
        },
    )

    assert response.status_code == 409
    assert response.json["error"] == "cycle_detected"


def test_post_reporting_lines_422s_for_a_self_reference(client, db):
    org_id = _seed_org(db)
    position_id = PositionRepo(org_id).create("CEO", "Executive")

    response = client.post(
        "/api/v1/org/reporting-lines",
        headers={"X-Org-Id": str(org_id)},
        json={
            "manager_id": str(position_id),
            "report_id": str(position_id),
            "relation": "solid",
            "is_primary": True,
        },
    )

    assert response.status_code == 422
    assert response.json["error"] == "validation_error"


def test_delete_reporting_lines_removes_an_edge(client, db):
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create("CEO", "Executive")
    vp = PositionRepo(org_id).create("VP", "Engineering")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    response = client.delete(
        "/api/v1/org/reporting-lines",
        headers={"X-Org-Id": str(org_id)},
        json={"manager_id": str(ceo), "report_id": str(vp)},
    )

    assert response.status_code == 200
    assert response.json["reports_to"] == []


def test_delete_reporting_lines_404s_when_no_such_edge(client, db):
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create("CEO", "Executive")
    vp = PositionRepo(org_id).create("VP", "Engineering")

    response = client.delete(
        "/api/v1/org/reporting-lines",
        headers={"X-Org-Id": str(org_id)},
        json={"manager_id": str(ceo), "report_id": str(vp)},
    )

    assert response.status_code == 404
