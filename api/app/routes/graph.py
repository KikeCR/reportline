"""GET /api/v1/org/graph?as_of=YYYY-MM-DD&view=positions|people."""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.models.api.common import ErrorOut, TenantHeader
from app.models.api.graph import EdgeOut, GraphOut, GraphQuery, NodeOut, OccupantOut
from app.services import org_graph

bp = APIBlueprint(
    "graph",
    __name__,
    url_prefix="/api/v1/org",
    abp_responses={422: ErrorOut},
)


@bp.get("/graph", summary="The full tenant org graph", responses={200: GraphOut})
def get_graph(query: GraphQuery, header: TenantHeader) -> tuple[dict[str, object], int]:
    graph = org_graph.get_graph(header.x_org_id, view=query.view, as_of=query.as_of)

    nodes = [
        NodeOut(
            id=node.id,
            title=node.title,
            department=node.department,
            status=node.status,
            occupants=(
                [
                    OccupantOut(
                        employee_id=o.employee_id, name=o.name, fte=o.fte, is_primary=o.is_primary
                    )
                    for o in graph.occupants[node.id]
                ]
                if query.view == "people"
                else None
            ),
        )
        for node in graph.nodes
    ]
    edges = [
        EdgeOut(
            report_id=edge.report_id,
            manager_id=edge.manager_id,
            relation=edge.relation,
            is_primary=edge.is_primary,
        )
        for edge in graph.edges
    ]
    out = GraphOut(nodes=nodes, edges=edges, root_ids=graph.root_ids)
    return out.model_dump(mode="json"), 200
