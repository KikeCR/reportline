"""Canonical Position model - see docs/data-model.md for field-by-field
constraints and docs/adr/0001-org-as-dag.md for why the graph is shaped
this way.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.common import MongoBaseModel, PyObjectId

# Real organizations don't exceed this; it also bounds reports_to's strict
# subset solid_manager_ids. See docs/data-model.md's "Why reports_to is
# capped at 8" note.
MAX_REPORTS_TO = 8


class PositionStatus(StrEnum):
    ACTIVE = "active"
    VACANT = "vacant"
    CLOSED = "closed"


class ReportsToEdge(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    position_id: PyObjectId
    relation: Literal["solid", "dotted"]
    is_primary: bool = False


class Position(MongoBaseModel):
    title: str = Field(min_length=1, max_length=200)
    department: str = Field(min_length=1, max_length=200)
    status: PositionStatus = PositionStatus.ACTIVE
    reports_to: list[ReportsToEdge] = Field(default_factory=list, max_length=MAX_REPORTS_TO)
    solid_manager_ids: list[PyObjectId] = Field(default_factory=list, max_length=MAX_REPORTS_TO)
    ancestor_ids: list[PyObjectId] = Field(default_factory=list)

    @model_validator(mode="after")
    def _at_most_one_primary_solid_edge(self) -> Self:
        primaries = [e for e in self.reports_to if e.relation == "solid" and e.is_primary]
        if len(primaries) > 1:
            raise ValueError("a position may have at most one primary solid reports_to edge")
        return self

    @model_validator(mode="after")
    def _solid_manager_ids_matches_reports_to(self) -> Self:
        expected = {e.position_id for e in self.reports_to if e.relation == "solid"}
        if set(self.solid_manager_ids) != expected:
            raise ValueError(
                "solid_manager_ids must exactly match the solid-relation position_ids in reports_to"
            )
        return self
