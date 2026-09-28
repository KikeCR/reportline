"""POST /api/v1/org/reporting-lines and DELETE /api/v1/org/reporting-lines."""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.models.api.common import ErrorOut, TenantHeader
from app.models.api.positions import PositionOut
from app.models.api.reporting_lines import ReportingLineDeleteIn, ReportingLineIn
from app.services import org_graph

bp = APIBlueprint(
    "reporting_lines",
    __name__,
    url_prefix="/api/v1/org/reporting-lines",
    abp_responses={404: ErrorOut, 409: ErrorOut, 422: ErrorOut},
)


@bp.post("", summary="Add a reporting line", responses={200: PositionOut})
def add_reporting_line(
    body: ReportingLineIn, header: TenantHeader
) -> tuple[dict[str, object], int]:
    updated = org_graph.add_reporting_line(
        header.x_org_id, body.manager_id, body.report_id, body.relation, body.is_primary
    )
    return PositionOut.from_position(updated).model_dump(mode="json"), 200


@bp.delete("", summary="Remove a reporting line", responses={200: PositionOut})
def remove_reporting_line(
    body: ReportingLineDeleteIn, header: TenantHeader
) -> tuple[dict[str, object], int]:
    updated = org_graph.remove_reporting_line(header.x_org_id, body.manager_id, body.report_id)
    return PositionOut.from_position(updated).model_dump(mode="json"), 200
