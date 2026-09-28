"""GET /api/v1/org/positions/{id} and GET /api/v1/org/positions/{id}/descendants."""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.models.api.common import ErrorOut, TenantHeader
from app.models.api.positions import DescendantOut, DescendantsOut, PositionOut, PositionPath
from app.services import org_graph

bp = APIBlueprint(
    "positions",
    __name__,
    url_prefix="/api/v1/org/positions",
    abp_responses={404: ErrorOut, 422: ErrorOut},
)


@bp.get("/<position_id>", summary="Get a position", responses={200: PositionOut})
def get_position(path: PositionPath, header: TenantHeader) -> tuple[dict[str, object], int]:
    position = org_graph.get_position(header.x_org_id, path.position_id)
    return PositionOut.from_position(position).model_dump(mode="json"), 200


@bp.get(
    "/<position_id>/descendants",
    summary="Solid-line subtree below a position",
    responses={200: DescendantsOut},
)
def get_descendants(path: PositionPath, header: TenantHeader) -> tuple[dict[str, object], int]:
    descendants = org_graph.get_descendants(header.x_org_id, path.position_id)
    results = [
        DescendantOut(
            id=d.position.id,
            title=d.position.title,
            department=d.position.department,
            status=d.position.status,
            reports_to=d.position.reports_to,
            depth=d.depth,
        )
        for d in descendants
    ]
    return DescendantsOut(results=results).model_dump(mode="json"), 200
