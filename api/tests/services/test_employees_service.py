from datetime import UTC, datetime
from decimal import Decimal

import pytest
from bson import ObjectId

from app.errors import NotFoundError
from app.repos import AssignmentRepo, EmployeeRepo, PositionRepo
from app.services.employees import get_employee

pytestmark = pytest.mark.integration


def test_get_employee_raises_not_found_for_unknown_id(db):
    with pytest.raises(NotFoundError):
        get_employee(ObjectId(), ObjectId())


def test_get_employee_has_no_title_without_a_current_assignment(db):
    org_id = ObjectId()
    employee_id = EmployeeRepo(org_id).create(
        "Ada Lovelace", "ada@example.com", compensation_amount=Decimal("100000")
    )

    view = get_employee(org_id, employee_id)

    assert view.employee.name == "Ada Lovelace"
    assert view.title is None


def test_get_employee_reports_current_primary_position_title(db):
    org_id = ObjectId()
    position_id = PositionRepo(org_id).create("VP Engineering", "Engineering")
    employee_id = EmployeeRepo(org_id).create(
        "Ada Lovelace", "ada@example.com", compensation_amount=Decimal("100000")
    )
    AssignmentRepo(org_id).create(employee_id, position_id, start_date=datetime.now(UTC))

    view = get_employee(org_id, employee_id)

    assert view.title == "VP Engineering"


def test_get_employee_prefers_the_primary_assignment_when_dual_role(db):
    org_id = ObjectId()
    primary_position = PositionRepo(org_id).create("VP Engineering", "Engineering")
    secondary_position = PositionRepo(org_id).create("VP Sales", "Sales")
    employee_id = EmployeeRepo(org_id).create(
        "Ada Lovelace", "ada@example.com", compensation_amount=Decimal("100000")
    )
    now = datetime.now(UTC)
    AssignmentRepo(org_id).create(
        employee_id, secondary_position, start_date=now, fte=0.5, is_primary=False
    )
    AssignmentRepo(org_id).create(
        employee_id, primary_position, start_date=now, fte=0.5, is_primary=True
    )

    view = get_employee(org_id, employee_id)

    assert view.title == "VP Engineering"
