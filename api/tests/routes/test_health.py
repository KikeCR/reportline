import pytest

pytestmark = pytest.mark.integration


def test_healthz_is_dependency_free(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_readyz_reports_mongo_ok(client):
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json == {"status": "ok", "mongo": "ok"}
