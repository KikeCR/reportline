from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.models.common import PyObjectId
from app.models.position import Position, PositionStatus, ReportsToEdge


class PositionPath(BaseModel):
    position_id: PyObjectId


class PositionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId
    title: str
    department: str
    status: PositionStatus
    reports_to: list[ReportsToEdge]

    @classmethod
    def from_position(cls, position: Position) -> PositionOut:
        return cls(
            id=position.id,
            title=position.title,
            department=position.department,
            status=position.status,
            reports_to=position.reports_to,
        )


class DescendantOut(PositionOut):
    depth: int = Field(description="Hops from the queried position, via solid lines only")


class DescendantsOut(BaseModel):
    results: list[DescendantOut]
