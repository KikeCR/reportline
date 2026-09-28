"""Canonical Employee model. Field-level exposure (e.g. compensation) is
controlled at the API boundary by which *out*-model a route uses, not here -
see api/app/models/employee_api.py once Phase 2 adds it.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import MongoBaseModel, PyDecimal128

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SourceRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    system: str = Field(min_length=1)
    id: str = Field(min_length=1)


class Compensation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: PyDecimal128
    currency: str = Field(min_length=3, max_length=3)


class Employee(MongoBaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: str
    source_refs: list[SourceRef] = Field(default_factory=list)
    compensation: Compensation

    @field_validator("email")
    @classmethod
    def _looks_like_an_email(cls, value: str) -> str:
        if not _EMAIL_RE.match(value):
            raise ValueError(f"{value!r} is not a valid email address")
        return value
