"""GET /api/v1/organizations - the tenant directory. The one endpoint with
no ``X-Org-Id`` header: a client can't know its org id without this.
"""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.models.api.organizations import OrganizationOut, OrganizationsOut
from app.services.organizations import list_organizations

bp = APIBlueprint("organizations", __name__, url_prefix="/api/v1/organizations")


@bp.get("/", summary="List organizations", responses={200: OrganizationsOut})
def list_organizations_route() -> tuple[dict[str, object], int]:
    docs = list_organizations()
    results = [OrganizationOut(id=d["_id"], name=d["name"]) for d in docs]
    return OrganizationsOut(results=results).model_dump(mode="json"), 200
