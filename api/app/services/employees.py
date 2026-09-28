"""Employee-facing reads. Joins an employee with their current primary
position's title, since the API's public employee view (CLAUDE.md /
Phase 4's ``EmployeePublicOut``) exposes title, not compensation.
"""

from __future__ import annotations

from dataclasses import dataclass

from bson import ObjectId

from app.errors import NotFoundError
from app.models.employee import Employee
from app.repos import AssignmentRepo, EmployeeRepo, PositionRepo


@dataclass(frozen=True)
class EmployeeView:
    employee: Employee
    title: str | None


def get_employee(org_id: ObjectId, employee_id: ObjectId) -> EmployeeView:
    employee_repo = EmployeeRepo(org_id)
    employee_doc = employee_repo.get_by_id(employee_id)
    if employee_doc is None:
        raise NotFoundError(f"employee {employee_id} not found")
    employee = Employee.model_validate(employee_doc)

    assignment_repo = AssignmentRepo(org_id)
    current_assignments = assignment_repo.current_for_employee(employee_id)
    primary_assignment = next(
        (a for a in current_assignments if a["is_primary"]),
        current_assignments[0] if current_assignments else None,
    )

    title: str | None = None
    if primary_assignment is not None:
        position_repo = PositionRepo(org_id)
        position_doc = position_repo.get_by_id(primary_assignment["position_id"])
        if position_doc is not None:
            title = position_doc["title"]

    return EmployeeView(employee=employee, title=title)
