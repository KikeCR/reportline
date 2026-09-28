from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from app.models.common import PyObjectId


class ReportingLineIn(BaseModel):
    manager_id: PyObjectId
    report_id: PyObjectId
    relation: Literal["solid", "dotted"]
    is_primary: bool = False


class ReportingLineDeleteIn(BaseModel):
    manager_id: PyObjectId
    report_id: PyObjectId
