"""The tenant registry - see docs/data-model.md for why this collection
exists beyond the brief's original Phase 1 list (it anchors org_id and
carries the org-level graph_version used for optimistic concurrency).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId


class Organization(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(alias="_id")
    name: str = Field(min_length=1)
    graph_version: int = 0
    schema_version: int = 1
    created_at: datetime
    updated_at: datetime
