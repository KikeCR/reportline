from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class SyncSourcePath(BaseModel):
    source: Literal["workday_like", "bamboo_like"]


class SyncRunOut(BaseModel):
    source: str
    created_count: int
    updated_count: int
    unchanged_count: int
    quarantined_count: int
    duration_ms: int
    started_at: datetime


class SyncRunsOut(BaseModel):
    results: list[SyncRunOut]


class QuarantineOut(BaseModel):
    source: str
    raw: dict[str, Any]
    errors: list[str]
    created_at: datetime


class QuarantineListOut(BaseModel):
    results: list[QuarantineOut]
