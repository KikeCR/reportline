"""Canonical Assignment model - the many-to-many join between an employee and
a position over time. See docs/data-model.md for why this isn't embedded on
either side.
"""

from __future__ import annotations

from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from app.models.common import MongoBaseModel, PyObjectId


class Assignment(MongoBaseModel):
    employee_id: PyObjectId
    position_id: PyObjectId
    start_date: datetime
    end_date: datetime | None = None
    fte: float = Field(gt=0, le=1)
    is_primary: bool = False

    @model_validator(mode="after")
    def _end_date_after_start_date(self) -> Self:
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self
