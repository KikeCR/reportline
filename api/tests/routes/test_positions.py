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


def test_get_position_returns_the_position(client, db):
    org_id = _seed_org(db)
    position_id = PositionRepo(org_id).create("VP Engineering", "Engineering")

    response = client.get(f"/api/v1/org/positions/{position_id}", headers={"X-Org-Id": str(org_id)})

    assert response.status_code == 200
    assert response.json["title"] == "VP Engineering"
    assert response.json["id"] == str(position_id)


def test_get_position_404s_for_unknown_id(client, db):
    org_id = _seed_org(db)

    response = client.get(f"/api/v1/org/positions/{ObjectId()}", headers={"X-Org-Id": str(org_id)})

    assert response.status_code == 404
    assert response.json["error"] == "not_found"


def test_get_position_is_tenant_isolated(client, db):
    org_a = _seed_org(db)
    org_b = _seed_org(db)
    position_id = PositionRepo(org_b).create("VP Engineering", "Engineering")

    response = client.get(f"/api/v1/org/positions/{position_id}", headers={"X-Org-Id": str(org_a)})

    assert response.status_code == 404


def test_get_position_422s_for_a_malformed_header(client, db):
    org_id = _seed_org(db)
    position_id = PositionRepo(org_id).create("VP Engineering", "Engineering")

    response = client.get(
        f"/api/v1/org/positions/{position_id}", headers={"X-Org-Id": "not-an-object-id"}
    )

    assert response.status_code == 422
    assert response.json["error"] == "validation_error"


def test_get_descendants_returns_the_solid_line_subtree(client, db):
    org_id = _seed_org(db)
    ceo = PositionRepo(org_id).create("CEO", "Executive")
    vp = PositionRepo(org_id).create("VP", "Engineering")
    org_graph.add_reporting_line(org_id, ceo, vp, "solid", True)

    response = client.get(
        f"/api/v1/org/positions/{ceo}/descendants", headers={"X-Org-Id": str(org_id)}
    )

    assert response.status_code == 200
    assert [r["title"] for r in response.json["results"]] == ["VP"]
    assert response.json["results"][0]["depth"] == 0


def test_get_descendants_404s_for_unknown_position(client, db):
    org_id = _seed_org(db)

    response = client.get(
        f"/api/v1/org/positions/{ObjectId()}/descendants", headers={"X-Org-Id": str(org_id)}
    )

    assert response.status_code == 404
