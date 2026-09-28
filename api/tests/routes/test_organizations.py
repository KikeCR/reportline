import pytest

from tests.factories import build_organization

pytestmark = pytest.mark.integration


def test_list_organizations_returns_every_org_sorted_by_name(client, db):
    db["organizations"].insert_one(build_organization(name="Zeta Corp"))
    db["organizations"].insert_one(build_organization(name="Acme Corp"))

    response = client.get("/api/v1/organizations/")

    assert response.status_code == 200
    names = [o["name"] for o in response.json["results"]]
    assert names == ["Acme Corp", "Zeta Corp"]
