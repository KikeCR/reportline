from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.models.common import PyObjectId
from app.models.position import PositionStatus


class GraphQuery(BaseModel):
    view: Literal["positions", "people"] = "positions"
    as_of: date | None = None


class OccupantOut(BaseModel):
    employee_id: PyObjectId
    name: str
    fte: float
    is_primary: bool


class NodeOut(BaseModel):
    id: PyObjectId
    title: str
    department: str
    status: PositionStatus
    occupants: list[OccupantOut] | None = None


class EdgeOut(BaseModel):
    report_id: PyObjectId
    manager_id: PyObjectId
    relation: Literal["solid", "dotted"]
    is_primary: bool


class GraphOut(BaseModel):
    nodes: list[NodeOut]
    edges: list[EdgeOut]
    root_ids: list[PyObjectId]
