"""GET /api/v1/employees/{id}.

Always returns ``EmployeePublicOut`` - never compensation - until Phase 4's
permission model exists to gate ``EmployeeHROut`` by role.
"""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.models.api.common import ErrorOut, TenantHeader
from app.models.api.employees import EmployeePath, EmployeePublicOut
from app.services.employees import get_employee

bp = APIBlueprint(
    "employees",
    __name__,
    url_prefix="/api/v1/employees",
    abp_responses={404: ErrorOut, 422: ErrorOut},
)


@bp.get(
    "/<employee_id>", summary="Get an employee (public view)", responses={200: EmployeePublicOut}
)
def get_employee_route(path: EmployeePath, header: TenantHeader) -> tuple[dict[str, object], int]:
    view = get_employee(header.x_org_id, path.employee_id)
    out = EmployeePublicOut(id=view.employee.id, name=view.employee.name, title=view.title)
    return out.model_dump(mode="json"), 200
