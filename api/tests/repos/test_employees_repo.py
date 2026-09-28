from decimal import Decimal

import pytest
from bson import ObjectId

from app.repos import EmployeeRepo
from tests.factories import build_employee

pytestmark = pytest.mark.integration


def test_create_round_trips_compensation_as_decimal128(db):
    org_id = ObjectId()
    repo = EmployeeRepo(org_id)

    employee_id = repo.create(
        "Ada Lovelace", "ada@example.com", compensation_amount=Decimal("150000.00")
    )

    doc = repo.get_by_id(employee_id)
    assert doc is not None
    assert doc["compensation"]["amount"].to_decimal() == Decimal("150000.00")
    assert doc["compensation"]["currency"] == "USD"
    assert doc["source_refs"] == []


def test_tenant_isolation_on_get_by_id(db):
    org_a, org_b = ObjectId(), ObjectId()
    employee_in_b = build_employee(org_b)
    db["employees"].insert_one(employee_in_b)

    repo_a = EmployeeRepo(org_a)

    assert repo_a.get_by_id(employee_in_b["_id"]) is None


def test_find_by_source_ref_matches_exact_pair(db):
    org_id = ObjectId()
    employee = build_employee(org_id, source_refs=[{"system": "workday_like", "id": "W-1"}])
    db["employees"].insert_one(employee)
    repo = EmployeeRepo(org_id)

    found = repo.find_by_source_ref("workday_like", "W-1")

    assert found is not None
    assert found["_id"] == employee["_id"]


def test_find_by_source_ref_does_not_cross_contaminate_across_systems(db):
    """The classic multi-key array pitfall: an employee with refs in two
    different systems must not false-match a (system, id) pair that spans
    both entries - this is exactly why EmployeeRepo uses $elemMatch.
    """
    org_id = ObjectId()
    employee = build_employee(
        org_id,
        source_refs=[
            {"system": "workday_like", "id": "W-1"},
            {"system": "bamboo_like", "id": "B-2"},
        ],
    )
    db["employees"].insert_one(employee)
    repo = EmployeeRepo(org_id)

    assert repo.find_by_source_ref("workday_like", "B-2") is None
    assert repo.find_by_source_ref("bamboo_like", "W-1") is None
    assert repo.find_by_source_ref("workday_like", "W-1") is not None
    assert repo.find_by_source_ref("bamboo_like", "B-2") is not None
