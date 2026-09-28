from __future__ import annotations

from pydantic import BaseModel

from app.models.common import PyObjectId


class OrganizationOut(BaseModel):
    id: PyObjectId
    name: str


class OrganizationsOut(BaseModel):
    results: list[OrganizationOut]
