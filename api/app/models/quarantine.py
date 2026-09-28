"""Canonical QuarantineRecord model. Written and read starting Phase 5
(services/sync.py); the collection itself is created in Phase 1's
migrations since it's part of the core data model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId


class QuarantineRecord(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(alias="_id")
    org_id: PyObjectId
    source: str
    raw: dict[str, Any]
    errors: list[str]
    created_at: datetime
