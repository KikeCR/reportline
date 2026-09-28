import pytest

from app.repos import OrganizationRepo

pytestmark = pytest.mark.integration


def test_create_starts_at_graph_version_zero(db):
    repo = OrganizationRepo()

    org_id = repo.create("Acme Corp")

    doc = repo.get_by_id(org_id)
    assert doc is not None
    assert doc["graph_version"] == 0
    assert doc["name"] == "Acme Corp"


def test_find_by_name_returns_none_when_absent(db):
    repo = OrganizationRepo()

    assert repo.find_by_name("Does Not Exist") is None


def test_find_by_name_finds_a_created_organization(db):
    repo = OrganizationRepo()
    org_id = repo.create("Findable Corp")

    found = repo.find_by_name("Findable Corp")

    assert found is not None
    assert found["_id"] == org_id


def test_delete_removes_the_organization(db):
    repo = OrganizationRepo()
    org_id = repo.create("Deletable Corp")

    repo.delete(org_id)

    assert repo.get_by_id(org_id) is None


def test_bump_graph_version_fails_when_version_does_not_match(db):
    repo = OrganizationRepo()
    org_id = repo.create("Versioned Corp")

    assert repo.bump_graph_version(org_id, expected_version=5) is False
    assert repo.get_by_id(org_id)["graph_version"] == 0

    assert repo.bump_graph_version(org_id, expected_version=0) is True
    assert repo.get_by_id(org_id)["graph_version"] == 1
