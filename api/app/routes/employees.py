"""GET /api/v1/employees/{id}.

No auth/roles (descoped by request - see README "Descoped"), so this always
returns the full HR view, including compensation.
"""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.models.api.common import ErrorOut, TenantHeader
from app.models.api.employees import CompensationOut, EmployeeHROut, EmployeePath
from app.services.employees import get_employee

bp = APIBlueprint(
    "employees",
    __name__,
    url_prefix="/api/v1/employees",
    abp_responses={404: ErrorOut, 422: ErrorOut},
)


@bp.get("/<employee_id>", summary="Get an employee", responses={200: EmployeeHROut})
def get_employee_route(path: EmployeePath, header: TenantHeader) -> tuple[dict[str, object], int]:
    view = get_employee(header.x_org_id, path.employee_id)
    out = EmployeeHROut(
        id=view.employee.id,
        name=view.employee.name,
        title=view.title,
        compensation=CompensationOut(
            amount=view.employee.compensation.amount,
            currency=view.employee.compensation.currency,
        ),
    )
    return out.model_dump(mode="json"), 200
