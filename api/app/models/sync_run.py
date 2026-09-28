"""A record of one sync run (Phase 5) - counts and duration, for GET
/admin/sync/runs.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId


class SyncRun(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(alias="_id")
    org_id: PyObjectId
    source: str
    created_count: int
    updated_count: int
    unchanged_count: int
    quarantined_count: int
    duration_ms: int
    started_at: datetime
