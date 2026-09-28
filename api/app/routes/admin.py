"""POST /api/v1/admin/sync/{source}, GET /api/v1/admin/sync/runs, GET /api/v1/admin/quarantine."""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.integrations.bamboo_like import BambooLikeAdapter
from app.integrations.base import Adapter
from app.integrations.workday_like import WorkdayLikeAdapter
from app.models.api.admin import (
    QuarantineListOut,
    QuarantineOut,
    SyncRunOut,
    SyncRunsOut,
    SyncSourcePath,
)
from app.models.api.common import ErrorOut, TenantHeader
from app.repos import QuarantineRepo, SyncRunRepo
from app.services.sync import run_sync

bp = APIBlueprint(
    "admin",
    __name__,
    url_prefix="/api/v1/admin",
    abp_responses={422: ErrorOut},
)

_ADAPTERS: dict[str, Adapter] = {
    "workday_like": WorkdayLikeAdapter(),
    "bamboo_like": BambooLikeAdapter(),
}


@bp.post("/sync/<source>", summary="Run a sync from an HRIS source", responses={200: SyncRunOut})
def run_sync_route(path: SyncSourcePath, header: TenantHeader) -> tuple[dict[str, object], int]:
    result = run_sync(header.x_org_id, _ADAPTERS[path.source])
    out = SyncRunOut(
        source=path.source,
        created_count=result.created,
        updated_count=result.updated,
        unchanged_count=result.unchanged,
        quarantined_count=result.quarantined,
        duration_ms=result.duration_ms,
        started_at=result.started_at,
    )
    return out.model_dump(mode="json"), 200


@bp.get("/sync/runs", summary="List past sync runs", responses={200: SyncRunsOut})
def list_sync_runs(header: TenantHeader) -> tuple[dict[str, object], int]:
    docs = SyncRunRepo(header.x_org_id).list_for_org()
    results = [
        SyncRunOut(
            source=d["source"],
            created_count=d["created_count"],
            updated_count=d["updated_count"],
            unchanged_count=d["unchanged_count"],
            quarantined_count=d["quarantined_count"],
            duration_ms=d["duration_ms"],
            started_at=d["started_at"],
        )
        for d in docs
    ]
    return SyncRunsOut(results=results).model_dump(mode="json"), 200


@bp.get("/quarantine", summary="List quarantined records", responses={200: QuarantineListOut})
def list_quarantine(header: TenantHeader) -> tuple[dict[str, object], int]:
    docs = QuarantineRepo(header.x_org_id).list_for_org()
    results = [
        QuarantineOut(
            source=d["source"], raw=d["raw"], errors=d["errors"], created_at=d["created_at"]
        )
        for d in docs
    ]
    return QuarantineListOut(results=results).model_dump(mode="json"), 200
