"""Shapes shared by every route: the one error format the whole API
returns, and the interim tenant header.

``TenantHeader`` is the single swap point for Phase 4's JWT: every route
reads the tenant via ``header: TenantHeader`` rather than a path/query
param, specifically so that replacing this one model (or how it's built)
with JWT-claim extraction is the only change routes need when auth lands -
route bodies never read a raw header themselves.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.models.common import PyObjectId


class ErrorOut(BaseModel):
    error: str = Field(description="A stable machine-readable error code, e.g. 'not_found'")
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class TenantHeader(BaseModel):
    x_org_id: PyObjectId = Field(
        description="Interim pre-auth tenant id - replaced by a JWT claim in Phase 4"
    )
