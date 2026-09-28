import pytest
from bson import ObjectId

from tests.factories import build_organization

pytestmark = pytest.mark.integration


def _seed_org(db) -> ObjectId:
    organization = build_organization()
    db["organizations"].insert_one(organization)
    return organization["_id"]


def test_run_sync_then_list_runs_and_quarantine(client, db):
    org_id = _seed_org(db)

    sync_response = client.post(
        "/api/v1/admin/sync/workday_like", headers={"X-Org-Id": str(org_id)}
    )
    assert sync_response.status_code == 200
    assert sync_response.json["created_count"] == 3
    assert sync_response.json["quarantined_count"] == 2

    runs_response = client.get("/api/v1/admin/sync/runs", headers={"X-Org-Id": str(org_id)})
    assert runs_response.status_code == 200
    assert len(runs_response.json["results"]) == 1

    quarantine_response = client.get("/api/v1/admin/quarantine", headers={"X-Org-Id": str(org_id)})
    assert quarantine_response.status_code == 200
    assert len(quarantine_response.json["results"]) == 2


def test_run_sync_422s_for_an_unknown_source(client, db):
    org_id = _seed_org(db)

    response = client.post("/api/v1/admin/sync/bogus_source", headers={"X-Org-Id": str(org_id)})

    assert response.status_code == 422
