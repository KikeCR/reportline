from datetime import UTC, datetime
from decimal import Decimal

import pytest
from bson import ObjectId

from app.repos import AssignmentRepo, EmployeeRepo, PositionRepo
from tests.factories import build_organization

pytestmark = pytest.mark.integration


def _seed_org(db) -> ObjectId:
    organization = build_organization()
    db["organizations"].insert_one(organization)
    return organization["_id"]


def test_get_employee_returns_full_hr_view(client, db):
    """No auth/roles for now (descoped) - every request sees compensation."""
    org_id = _seed_org(db)
    position_id = PositionRepo(org_id).create("VP Engineering", "Engineering")
    employee_id = EmployeeRepo(org_id).create(
        "Ada Lovelace", "ada@example.com", compensation_amount=Decimal("150000")
    )
    AssignmentRepo(org_id).create(employee_id, position_id, start_date=datetime.now(UTC))

    response = client.get(f"/api/v1/employees/{employee_id}", headers={"X-Org-Id": str(org_id)})

    assert response.status_code == 200
    assert response.json == {
        "id": str(employee_id),
        "name": "Ada Lovelace",
        "title": "VP Engineering",
        "compensation": {"amount": "150000", "currency": "USD"},
    }


def test_get_employee_404s_for_unknown_id(client, db):
    org_id = _seed_org(db)

    response = client.get(f"/api/v1/employees/{ObjectId()}", headers={"X-Org-Id": str(org_id)})

    assert response.status_code == 404
