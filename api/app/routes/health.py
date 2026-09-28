"""GET /healthz (dependency-free) and GET /readyz (checks Mongo)."""

from __future__ import annotations

from flask_openapi3.blueprint import APIBlueprint

from app.models.api.health import HealthOut, ReadyOut
from app.services import health as health_service

bp = APIBlueprint("health", __name__)


@bp.get("/healthz", summary="Liveness check", responses={200: HealthOut})
def healthz() -> tuple[dict[str, object], int]:
    return HealthOut(status="ok").model_dump(mode="json"), 200


@bp.get(
    "/readyz",
    summary="Readiness check (verifies Mongo connectivity)",
    responses={200: ReadyOut, 503: ReadyOut},
)
def readyz() -> tuple[dict[str, object], int]:
    mongo_ok = health_service.check_database()
    status = "ok" if mongo_ok else "error"
    out = ReadyOut(status=status, mongo="ok" if mongo_ok else "error")
    return out.model_dump(mode="json"), 200 if mongo_ok else 503
